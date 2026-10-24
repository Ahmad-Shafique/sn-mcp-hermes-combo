"""Tier 3 - QA tests. The entry point and the composition root."""

from __future__ import annotations

import pytest

from snowmcp.infrastructure.config import Settings
from snowmcp.infrastructure.wiring import build_gateway, build_services
from snowmcp.adapters.http.client import ServiceNowClient

from tests.conftest import FakeGateway


def test_the_entry_point_refuses_to_start_without_configuration(monkeypatch, capsys) -> None:
    """A missing instance URL must fail loudly, not start a broken server."""
    from snowmcp.__main__ import main

    monkeypatch.setenv("SN_INSTANCE_URL", "")
    monkeypatch.setenv("SN_USERNAME", "")

    assert main() == 2
    assert "SN_INSTANCE_URL is required" in capsys.readouterr().err


def test_the_entry_point_starts_the_server(monkeypatch) -> None:
    """With configuration present, the server is built and run on stdio."""
    from snowmcp import __main__ as entry

    started = {}

    class FakeServer:
        def run(self, transport=None):
            started["transport"] = transport

    monkeypatch.setenv("SN_INSTANCE_URL", "https://example.service-now.com")
    monkeypatch.setenv("SN_USERNAME", "user")
    monkeypatch.setenv("SN_PASSWORD", "secret")
    monkeypatch.setenv("SN_STORE_PATH", ":memory:")
    monkeypatch.setattr(entry, "build_server", lambda services: FakeServer())

    assert entry.main() == 0
    assert started["transport"] == "stdio"


def test_the_composition_root_builds_a_real_transport() -> None:
    """Without an injected gateway, the root builds the HTTP client."""
    settings = Settings(instance_url="https://example.service-now.com", username="u", password="p")

    gateway = build_gateway(settings)

    assert isinstance(gateway, ServiceNowClient)


def test_the_composition_root_builds_every_use_case(gateway: FakeGateway, store) -> None:
    settings = Settings(instance_url="https://example.service-now.com", store_path=":memory:")

    services = build_services(settings, gateway=gateway, store=store)

    assert services.records is not None
    assert services.graph is not None
    assert services.knowledge is not None
    assert services.undo is not None
