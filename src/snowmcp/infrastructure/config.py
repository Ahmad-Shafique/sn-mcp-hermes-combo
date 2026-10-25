"""Configuration, read from the environment.

Every setting has a safe default except the instance URL and one credential,
which the server cannot work without.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from snowmcp.domain.errors import ConfigurationError
from snowmcp.domain.policy import WritePolicy

DEFAULT_STORE_PATH = "~/.hermes/data/snowmcp/store.sqlite3"


@dataclass(frozen=True)
class Settings:
    """Everything the server needs to start."""

    instance_url: str = ""
    username: str = ""
    password: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_token_url: str = ""
    scripted_rest_url: str = ""
    timeout: int = 60
    max_bytes: int = 8 * 1024 * 1024
    store_path: str = DEFAULT_STORE_PATH
    read_only: bool = False
    allowed_tables: frozenset[str] = field(default_factory=frozenset)
    denied_tables: frozenset[str] = field(default_factory=frozenset)
    require_confirm: bool = True
    max_batch: int = 100

    @property
    def policy(self) -> WritePolicy:
        """The write policy implied by these settings."""
        return WritePolicy(
            read_only=self.read_only,
            allowed_tables=self.allowed_tables,
            denied_tables=self.denied_tables,
            require_confirm=self.require_confirm,
            max_batch=self.max_batch,
        )

    @property
    def resolved_store_path(self) -> Path:
        """The store path, expanded."""
        return Path(self.store_path).expanduser()

    def validate(self) -> None:
        """Fail fast, and clearly, when the instance is not configured."""
        if not self.instance_url:
            raise ConfigurationError(
                "SN_INSTANCE_URL is required (e.g. https://yourcompany.service-now.com)"
            )
        if not self.instance_url.startswith(("https://", "http://")):
            raise ConfigurationError(
                f"SN_INSTANCE_URL must start with https:// or http://, got {self.instance_url!r}"
            )
        if not (self.username or self.oauth_client_id):
            raise ConfigurationError(
                "credentials are required: set SN_USERNAME and SN_PASSWORD, "
                "or SN_OAUTH_CLIENT_ID and SN_OAUTH_CLIENT_SECRET"
            )


def _csv(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip() for part in value.split(",") if part.strip())


def _int(value: str | None, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Build settings from the environment."""
    env = os.environ if environ is None else environ
    return Settings(
        instance_url=env.get("SN_INSTANCE_URL", "").strip(),
        username=env.get("SN_USERNAME", "").strip(),
        password=env.get("SN_PASSWORD", ""),
        oauth_client_id=env.get("SN_OAUTH_CLIENT_ID", "").strip(),
        oauth_client_secret=env.get("SN_OAUTH_CLIENT_SECRET", ""),
        oauth_token_url=env.get("SN_OAUTH_TOKEN_URL", "").strip(),
        scripted_rest_url=env.get("SN_SCRIPTED_REST_URL", "").strip(),
        timeout=_int(env.get("SN_TIMEOUT"), 60),
        max_bytes=_int(env.get("SN_MAX_BYTES"), 8 * 1024 * 1024),
        store_path=env.get("SN_STORE_PATH", DEFAULT_STORE_PATH).strip() or DEFAULT_STORE_PATH,
        read_only=_bool(env.get("SN_READ_ONLY"), False),
        allowed_tables=_csv(env.get("SN_ALLOWED_TABLES")),
        denied_tables=_csv(env.get("SN_DENIED_TABLES")),
        require_confirm=_bool(env.get("SN_REQUIRE_CONFIRM"), True),
        max_batch=_int(env.get("SN_MAX_BATCH"), 100),
    )
