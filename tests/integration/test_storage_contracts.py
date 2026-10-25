"""Tier 2 - contract tests for the local storage payloads and OAuth.

The journal and history records are what an operator reads when something goes
wrong, so their exact shape is a contract, not an implementation detail.
"""

from __future__ import annotations

import json
import urllib.request

import pytest

from snowmcp.adapters.http.client import ServiceNowClient
from snowmcp.domain.storage import (
    CachedRecord,
    CallRecord,
    JournalEntry,
    JournalView,
    Note,
    SavedQuery,
)


class TestStoragePayloads:
    """The exact shape of every stored payload."""

    def test_a_note_payload_has_exactly_these_keys(self) -> None:
        note = Note(key="runbook", title="Runbook", body="steps", tags=("ops",))

        assert note.to_dict() == {
            "key": "runbook",
            "title": "Runbook",
            "body": "steps",
            "tags": ["ops"],
            "updated_at": note.updated_at,
        }

    def test_a_cached_record_payload_has_exactly_these_keys(self) -> None:
        record = CachedRecord(table="incident", sys_id="abc", payload={"number": "INC01"})

        assert record.to_dict() == {
            "table": "incident",
            "sys_id": "abc",
            "payload": {"number": "INC01"},
            "fetched_at": record.fetched_at,
        }

    def test_a_saved_query_payload_has_exactly_these_keys(self) -> None:
        query = SavedQuery(
            name="open", table="incident", encoded_query="state=2", fields=("number",), limit=7
        )

        assert query.to_dict() == {
            "name": "open",
            "table": "incident",
            "encoded_query": "state=2",
            "fields": ["number"],
            "limit": 7,
            "created_at": query.created_at,
        }

    def test_a_call_record_payload_has_exactly_these_keys(self) -> None:
        call = CallRecord(tool="sn_read", summary="query incident")

        assert call.to_dict() == {
            "tool": "sn_read",
            "summary": "query incident",
            "at": call.at,
        }

    def test_a_journal_entry_payload_has_exactly_these_keys(self) -> None:
        entry = JournalEntry(
            entry_id="create:incident:abc",
            operation="create",
            table="incident",
            sys_id="abc",
            before=None,
            after={"short_description": "x"},
        )

        assert entry.to_dict() == {
            "entry_id": "create:incident:abc",
            "operation": "create",
            "table": "incident",
            "sys_id": "abc",
            "before": None,
            "after": {"short_description": "x"},
            "at": entry.at,
            "reverted": False,
        }

    def test_a_journal_entry_keeps_its_before_and_after(self) -> None:
        entry = JournalEntry(
            entry_id="update:incident:abc",
            operation="update",
            table="incident",
            sys_id="abc",
            before={"state": "2"},
            after={"state": "3"},
            reverted=True,
        )

        payload = entry.to_dict()

        assert payload["before"] == {"state": "2"}
        assert payload["after"] == {"state": "3"}
        assert payload["reverted"] is True

    def test_a_journal_view_wraps_its_entry_and_plan(self) -> None:
        entry = JournalEntry(
            entry_id="create:incident:abc", operation="create", table="incident", sys_id="abc"
        )
        view = JournalView(entry=entry, plan="delete incident/abc")

        assert view.to_dict() == {"entry": entry.to_dict(), "plan": "delete incident/abc"}


class TestOAuthContract:
    """The exact request the token exchange makes."""

    def test_the_token_request_is_a_form_post_to_the_token_url(self, monkeypatch) -> None:
        calls: list[dict[str, object]] = []

        class FakeResponse:
            status = 200
            headers: dict[str, str] = {}

            def read(self) -> bytes:
                return b'{"access_token": "tok-123", "expires_in": 600}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        def fake_urlopen(request, timeout=None):
            calls.append(
                {
                    "url": request.full_url,
                    "method": request.get_method(),
                    "body": request.data.decode() if request.data else None,
                    "content_type": request.headers.get("Content-type"),
                }
            )
            return FakeResponse()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        client = ServiceNowClient(
            "https://example.service-now.com",
            oauth_client_id="my-id",
            oauth_client_secret="my-secret",
            oauth_token_url="https://example.service-now.com/oauth_token.do",
        )

        client.request("GET", "/api/now/table/incident")

        token_call = calls[0]
        assert token_call["url"] == "https://example.service-now.com/oauth_token.do"
        assert token_call["method"] == "POST"
        assert "grant_type=client_credentials" in token_call["body"]
        assert "client_id=my-id" in token_call["body"]
        assert "client_secret=my-secret" in token_call["body"]
        assert "form-urlencoded" in str(token_call["content_type"]).lower()

    def test_the_api_call_carries_the_bearer_token(self, monkeypatch) -> None:
        seen: dict[str, object] = {}

        class FakeResponse:
            status = 200
            headers: dict[str, str] = {}

            def __init__(self, body: bytes) -> None:
                self._body = body

            def read(self) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        def fake_urlopen(request, timeout=None):
            if "oauth_token.do" in request.full_url:
                return FakeResponse(b'{"access_token": "tok-123", "expires_in": 600}')
            seen["auth"] = request.headers.get("Authorization")
            return FakeResponse(b'{"result": []}')

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        client = ServiceNowClient(
            "https://example.service-now.com",
            oauth_client_id="my-id",
            oauth_client_secret="my-secret",
            oauth_token_url="https://example.service-now.com/oauth_token.do",
        )

        client.request("GET", "/api/now/table/incident")

        assert seen["auth"] == "Bearer tok-123"

    def test_the_backoff_honours_retry_after(self) -> None:
        client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

        assert client._backoff(_http_error(429, {"Retry-After": "7"}), 1) == 7.0

    def test_the_backoff_uses_exponential_steps_without_retry_after(self) -> None:
        client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

        assert client._backoff(None, 1) == 1.0
        assert client._backoff(None, 2) == 2.0
        assert client._backoff(None, 3) == 4.0

    def test_the_backoff_is_capped(self) -> None:
        client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

        assert client._backoff(None, 20) == 30.0


def _http_error(code: int, headers: dict[str, str]):
    """Build an HTTPError the way urllib raises one."""
    import io
    import urllib.error

    return urllib.error.HTTPError(
        url="https://example.service-now.com",
        code=code,
        msg="error",
        hdrs=headers,
        fp=io.BytesIO(b"{}"),
    )
