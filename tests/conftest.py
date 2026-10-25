"""Shared fixtures.

The tests never touch the network. A fake gateway stands in for the instance
so every layer can be exercised deterministically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pytest
from hypothesis import HealthCheck, settings as hypothesis_settings

from snowmcp.adapters.store.sqlite import SQLiteStore
from snowmcp.application.ports import Response
from snowmcp.domain.policy import WritePolicy
from snowmcp.infrastructure.config import Settings
from snowmcp.infrastructure.wiring import build_services


def _under_mutation_testing() -> bool:
    """True when pytest is running inside mutmut's copied tree."""
    if os.environ.get("MUTMUT_UNDER_TEST"):
        return True
    return "mutants" in Path.cwd().parts


if _under_mutation_testing():
    # mutmut forks a fresh worker per mutant, so Hypothesis sees the same
    # test run by several executors and trips `differing_executors`. The
    # health check is protecting the example database, so the fix is to
    # remove the database (`database=None`) rather than to mute the warning
    # alone. The deadline is also disabled: a mutated function can be
    # arbitrarily slow, and a timing failure would count as a false kill.
    hypothesis_settings.register_profile(
        "mutation_safe",
        database=None,
        deadline=None,
        # The default is 100 examples per property. Under mutation testing
        # each mutant runs the suite again, so 25 examples is enough to
        # catch a broken invariant and a quarter of the time.
        max_examples=25,
        suppress_health_check=[HealthCheck.differing_executors],
    )
    hypothesis_settings.load_profile("mutation_safe")


@dataclass
class RecordedCall:
    """One request the fake gateway received."""

    method: str
    path: str
    params: Mapping[str, str] | None = None
    json_body: Any = None


@dataclass
class FakeGateway:
    """An ``InstanceGateway`` that replays canned responses."""

    responses: dict[str, Response] = field(default_factory=dict)
    default: Response | None = None
    calls: list[RecordedCall] = field(default_factory=list)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """Return the canned response for this path, recording the call."""
        self.calls.append(RecordedCall(method, path, params, json_body))
        if path in self.responses:
            return self.responses[path]
        if self.default is not None:
            return self.default
        return Response(status=200, body={"result": []})

    def last(self) -> RecordedCall:
        """The most recent call."""
        return self.calls[-1]

    def paths(self) -> list[str]:
        """Every path requested, in order."""
        return [call.path for call in self.calls]


def ok(body: Any) -> Response:
    """A 200 response carrying a JSON body."""
    return Response(status=200, body=body)


def records(*items: dict[str, Any]) -> Response:
    """A 200 response carrying a Table API result list."""
    return Response(status=200, body={"result": list(items)})


@pytest.fixture
def gateway() -> FakeGateway:
    """A fake instance."""
    return FakeGateway()


@pytest.fixture
def store() -> SQLiteStore:
    """An in-memory local store."""
    return SQLiteStore(":memory:")


@pytest.fixture
def policy() -> WritePolicy:
    """A permissive write policy: writes still need confirmation."""
    return WritePolicy(require_confirm=True)


@pytest.fixture
def settings() -> Settings:
    """Settings pointing at a fictional instance."""
    return Settings(
        instance_url="https://example.service-now.com",
        username="user",
        password="secret",
        store_path=":memory:",
    )


@pytest.fixture
def services(gateway: FakeGateway, store: SQLiteStore, settings: Settings):
    """Every use case wired to the fake gateway and the in-memory store."""
    return build_services(settings, gateway=gateway, store=store)
