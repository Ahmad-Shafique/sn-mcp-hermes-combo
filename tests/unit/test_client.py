"""Tier 1 - unit tests for the HTTP transport.

The network is stubbed at ``urllib.request.urlopen``; nothing here opens a
socket.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from snowmcp.adapters.http.client import ServiceNowClient
from snowmcp.domain.errors import AuthenticationError, ConfigurationError, ServiceNowAPIError


class FakeHTTPResponse:
    """A minimal stand-in for an urllib response object."""

    def __init__(self, status: int = 200, body: bytes = b"{}", headers: dict[str, str] | None = None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def http_error(code: int, body: bytes = b"{}", headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    """Build an HTTPError the way urllib would raise one."""
    return urllib.error.HTTPError(
        url="https://example.service-now.com/api/now/table/incident",
        code=code,
        msg="error",
        hdrs=headers or {},
        fp=io.BytesIO(body),
    )


def test_a_get_returns_the_decoded_body(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["headers"] = request.headers
        seen["method"] = request.get_method()
        return FakeHTTPResponse(200, json.dumps({"result": []}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    response = client.request("GET", "/api/now/table/incident", params={"sysparm_limit": "5"})

    assert response.status == 200
    assert response.body == {"result": []}
    assert "sysparm_limit=5" in str(seen["url"])
    assert seen["method"] == "GET"


def test_basic_auth_is_sent(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        seen["auth"] = request.headers.get("Authorization")
        return FakeHTTPResponse(200, b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    client.request("GET", "/api/now/table/incident")

    assert str(seen["auth"]).startswith("Basic ")


def test_a_json_body_is_encoded(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        seen["data"] = request.data
        seen["content_type"] = request.headers.get("Content-type")
        return FakeHTTPResponse(200, b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    client.request("POST", "/api/now/table/incident", json_body={"a": 1})

    assert json.loads(seen["data"]) == {"a": 1}
    assert "json" in str(seen["content_type"]).lower()


def test_missing_credentials_are_refused(monkeypatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse())
    client = ServiceNowClient("https://example.service-now.com")

    with pytest.raises(AuthenticationError, match=r"^no credentials configured for the ServiceNow instance$"):
        client.request("GET", "/api/now/table/incident")


def test_an_http_error_is_returned_rather_than_raised(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise http_error(404, b'{"error": {"message": "no such record"}}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    response = client.request("GET", "/api/now/table/incident/abc")

    assert response.status == 404
    assert response.body == {"error": {"message": "no such record"}}


def test_a_server_error_is_retried_then_returned(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise http_error(500, b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com", username="u", password="p", max_retries=2, sleep=lambda _: None
    )

    response = client.request("GET", "/api/now/table/incident")

    assert response.status == 500
    assert calls["n"] == 3


def test_a_rate_limit_is_retried(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise http_error(429, b"{}", {"Retry-After": "1"})
        return FakeHTTPResponse(200, b'{"result": []}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com", username="u", password="p", max_retries=2, sleep=lambda _: None
    )

    response = client.request("GET", "/api/now/table/incident")

    assert response.status == 200
    assert calls["n"] == 2


def test_a_connection_failure_is_retried_then_raised(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com", username="u", password="p", max_retries=1, sleep=lambda _: None
    )

    with pytest.raises(ServiceNowAPIError, match=r"^cannot reach https://example.service-now.com: connection refused$"):
        client.request("GET", "/api/now/table/incident")


def test_a_non_json_body_is_returned_as_text(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse(200, b"plain text")
    )
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    assert client.request("GET", "/api/now/table/incident").body == "plain text"


def test_an_empty_body_decodes_to_none(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse(200, b"")
    )
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    assert client.request("GET", "/api/now/table/incident").body is None


def test_an_oversized_response_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse(200, b"x" * 100)
    )
    client = ServiceNowClient(
        "https://example.service-now.com", username="u", password="p", max_bytes=10
    )

    with pytest.raises(ServiceNowAPIError, match=r"^response exceeded the 10 byte limit$"):
        client.request("GET", "/api/now/table/incident")


def test_an_oauth_token_is_fetched_and_reused(monkeypatch) -> None:
    calls = {"token": 0, "api": 0}

    def fake_urlopen(request, timeout=None):
        if request.full_url == "https://example.service-now.com/oauth/token.do":
            calls["token"] += 1
            return FakeHTTPResponse(200, b'{"access_token": "tok-123", "expires_in": 600}')
        calls["api"] += 1
        return FakeHTTPResponse(200, b'{"result": []}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com",
        oauth_client_id="id",
        oauth_client_secret="secret",
        oauth_token_url="https://example.service-now.com/oauth/token.do",
    )

    client.request("GET", "/api/now/table/incident")
    client.request("GET", "/api/now/table/incident")

    assert calls["token"] == 1
    assert calls["api"] == 2


def test_a_failing_token_endpoint_raises(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise http_error(401, b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com",
        oauth_client_id="id",
        oauth_client_secret="secret",
        oauth_token_url="https://example.service-now.com/oauth/token.do",
    )

    with pytest.raises(AuthenticationError, match=r"^token endpoint returned HTTP 401$"):
        client.request("GET", "/api/now/table/incident")


def test_an_unreachable_token_endpoint_raises(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient(
        "https://example.service-now.com",
        oauth_client_id="id",
        oauth_client_secret="secret",
        oauth_token_url="https://example.service-now.com/oauth/token.do",
    )

    with pytest.raises(AuthenticationError, match=r"^cannot reach the token endpoint: no route to host$"):
        client.request("GET", "/api/now/table/incident")


def test_a_token_response_without_a_token_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse(200, b'{"nope": 1}')
    )
    client = ServiceNowClient(
        "https://example.service-now.com",
        oauth_client_id="id",
        oauth_client_secret="secret",
        oauth_token_url="https://example.service-now.com/oauth/token.do",
    )

    with pytest.raises(AuthenticationError, match=r"^the token endpoint did not return an access_token$"):
        client.request("GET", "/api/now/table/incident")


def test_oauth_without_a_token_url_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=None: FakeHTTPResponse())
    client = ServiceNowClient("https://example.service-now.com", oauth_client_id="id")

    with pytest.raises(ConfigurationError, match=r"^SN_OAUTH_TOKEN_URL is required when using OAuth$"):
        client.request("GET", "/api/now/table/incident")
