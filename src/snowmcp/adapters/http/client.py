"""HTTP transport to a ServiceNow instance.

Pure transport: it knows how to connect, authenticate, retry and decode. It
knows nothing about CIs, catalog items or impact analysis - that knowledge
lives in the application layer.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from snowmcp.application.ports import Response
from snowmcp.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    ServiceNowAPIError,
)

DEFAULT_TIMEOUT = 60
DEFAULT_MAX_BYTES = 8 * 1024 * 1024


class ServiceNowClient:
    """An ``InstanceGateway`` over the ServiceNow REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        username: str = "",
        password: str = "",
        oauth_client_id: str = "",
        oauth_client_secret: str = "",
        oauth_token_url: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_retries: int = 3,
        sleep: Any = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._oauth_client_id = oauth_client_id
        self._oauth_client_secret = oauth_client_secret
        self._oauth_token_url = oauth_token_url
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._max_retries = max_retries
        self._sleep = sleep
        self._token = ""
        self._token_expires_at = 0.0

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """Perform one request against the instance."""
        url = self._build_url(path, params)
        data = None
        request_headers = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        request_headers["Authorization"] = self._authorization_header()

        attempt = 0
        while True:
            attempt += 1
            request = urllib.request.Request(
                url, data=data, headers=request_headers, method=method.upper()
            )
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    body = self._decode(response.read())
                    return Response(
                        status=response.status,
                        body=body,
                        headers={key.lower(): value for key, value in response.headers.items()},
                    )
            except urllib.error.HTTPError as exc:
                body = self._decode(exc.read())
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt <= self._max_retries:
                        self._sleep(self._backoff(exc, attempt))
                        continue
                return Response(status=exc.code, body=body)
            except urllib.error.URLError as exc:
                if attempt <= self._max_retries:
                    self._sleep(self._backoff(None, attempt))
                    continue
                raise ServiceNowAPIError(f"cannot reach {self._base_url}: {exc.reason}") from exc
            except TimeoutError as exc:
                raise ServiceNowAPIError(f"request to {url} timed out after {self._timeout}s") from exc

    def _build_url(self, path: str, params: Mapping[str, str] | None) -> str:
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url

    def _authorization_header(self) -> str:
        if self._oauth_client_id:
            return f"Bearer {self._access_token()}"
        if self._username:
            raw = f"{self._username}:{self._password}".encode("utf-8")
            return f"Basic {base64.b64encode(raw).decode('ascii')}"
        raise AuthenticationError("no credentials configured for the ServiceNow instance")

    def _access_token(self) -> str:
        """Fetch (and cache) an OAuth2 client-credentials token."""
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token
        if not self._oauth_token_url:
            raise ConfigurationError("SN_OAUTH_TOKEN_URL is required when using OAuth")
        payload = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._oauth_client_id,
                "client_secret": self._oauth_client_secret,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._oauth_token_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = self._decode(response.read())
        except urllib.error.HTTPError as exc:
            raise AuthenticationError(
                f"token endpoint returned HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AuthenticationError(f"cannot reach the token endpoint: {exc.reason}") from exc
        if not isinstance(body, dict) or "access_token" not in body:
            raise AuthenticationError("the token endpoint did not return an access_token")
        self._token = str(body["access_token"])
        expires_in = body.get("expires_in")
        ttl = int(expires_in) if isinstance(expires_in, (int, float, str)) and str(expires_in).isdigit() else 300
        self._token_expires_at = time.time() + max(30, ttl - 30)
        return self._token

    def _decode(self, raw: bytes) -> Any:
        """Decode a response body, guarding against an oversized payload."""
        if len(raw) > self._max_bytes:
            raise ServiceNowAPIError(
                f"response exceeded the {self._max_bytes} byte limit"
            )
        if not raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except ValueError:
            return text

    def _backoff(self, error: urllib.error.HTTPError | None, attempt: int) -> float:
        """Wait before retrying: honour Retry-After, else exponential backoff."""
        if error is not None:
            retry_after = error.headers.get("Retry-After") if error.headers else None
            if retry_after and retry_after.isdigit():
                return min(float(retry_after), 30.0)
        return min(2.0 ** (attempt - 1), 30.0)
