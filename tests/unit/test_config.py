"""Tier 1 - unit tests for configuration loading."""

from __future__ import annotations

import pytest

from snowmcp.domain.errors import ConfigurationError
from snowmcp.infrastructure.config import Settings, load_settings


def test_settings_default_to_requiring_confirmation() -> None:
    assert Settings().require_confirm is True


def test_settings_expose_their_write_policy() -> None:
    policy = Settings(read_only=True, allowed_tables=frozenset({"incident"})).policy
    assert policy.read_only is True
    assert policy.allowed_tables == frozenset({"incident"})


def test_the_store_path_is_expanded() -> None:
    assert "~" not in str(Settings(store_path="~/.hermes/x.sqlite3").resolved_store_path)


def test_validation_requires_an_instance_url() -> None:
    with pytest.raises(
        ConfigurationError, match=r"^SN_INSTANCE_URL is required .*$"
    ):
        Settings().validate()


def test_validation_requires_an_https_url() -> None:
    with pytest.raises(
        ConfigurationError, match=r"^SN_INSTANCE_URL must start with https:// or http://.*$"
    ):
        Settings(instance_url="example.service-now.com", username="u").validate()


def test_validation_requires_credentials() -> None:
    with pytest.raises(ConfigurationError, match=r"^credentials are required: .*$"):
        Settings(instance_url="https://example.service-now.com").validate()


def test_validation_accepts_basic_credentials() -> None:
    Settings(instance_url="https://example.service-now.com", username="u", password="p").validate()


def test_validation_accepts_oauth_credentials() -> None:
    Settings(
        instance_url="https://example.service-now.com", oauth_client_id="id", oauth_client_secret="s"
    ).validate()


def test_settings_are_read_from_the_environment() -> None:
    settings = load_settings(
        {
            "SN_INSTANCE_URL": "https://example.service-now.com",
            "SN_USERNAME": "user",
            "SN_PASSWORD": "secret",
            "SN_READ_ONLY": "true",
            "SN_ALLOWED_TABLES": "incident, change_request",
            "SN_MAX_BATCH": "25",
            "SN_TIMEOUT": "30",
        }
    )

    assert settings.username == "user"
    assert settings.read_only is True
    assert settings.allowed_tables == frozenset({"incident", "change_request"})
    assert settings.max_batch == 25
    assert settings.timeout == 30


def test_a_missing_environment_variable_falls_back_to_the_default() -> None:
    assert load_settings({}).timeout == 60
    assert load_settings({}).store_path.endswith("store.sqlite3")


def test_a_non_numeric_environment_value_falls_back_to_the_default() -> None:
    assert load_settings({"SN_TIMEOUT": "not a number"}).timeout == 60


def test_a_non_numeric_batch_limit_falls_back_to_the_default() -> None:
    assert load_settings({"SN_MAX_BATCH": "lots"}).max_batch == 100


def test_an_empty_table_list_is_empty() -> None:
    assert load_settings({"SN_ALLOWED_TABLES": ""}).allowed_tables == frozenset()


def test_a_read_only_flag_is_parsed_from_common_truthy_spellings() -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert load_settings({"SN_READ_ONLY": value}).read_only is True
    assert load_settings({"SN_READ_ONLY": "0"}).read_only is False
