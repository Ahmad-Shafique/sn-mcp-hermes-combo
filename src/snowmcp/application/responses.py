"""Turning raw responses into domain results or domain errors.

Which HTTP status means which failure is policy, so it lives in the
application layer. The adapter's job stops at transport: connect, send,
receive.
"""

from __future__ import annotations

from typing import Any

from snowmcp.application.ports import Response
from snowmcp.domain.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ServiceNowAPIError,
)


def error_detail(body: Any) -> str | None:
    """Pull the human-readable message out of a ServiceNow error body."""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail")
            if isinstance(message, str):
                return message
        for key in ("message", "detail"):
            value = body.get(key)
            if isinstance(value, str):
                return value
    if isinstance(body, str) and body.strip():
        return body[:500]
    return None


def unwrap(response: Response) -> Any:
    """Return the response body, or raise the domain error it represents."""
    if response.ok:
        return response.body
    detail = error_detail(response.body)
    message = detail or f"ServiceNow returned HTTP {response.status}"
    if response.status in (401, 403):
        if response.status == 401:
            raise AuthenticationError(message)
        raise PermissionDeniedError(message)
    if response.status == 404:
        raise NotFoundError(message)
    raise ServiceNowAPIError(message, status=response.status, detail=detail, body=response.body)


def unwrap_records(response: Response) -> dict[str, Any]:
    """Unwrap a Table API result, guaranteeing a mapping."""
    body = unwrap(response)
    if not isinstance(body, dict):
        raise ServiceNowAPIError(
            "expected a JSON object from the Table API",
            status=response.status,
            body=body,
        )
    return body


def unwrap_list(response: Response) -> list[Any]:
    """Unwrap a result that should be a JSON array."""
    body = unwrap(response)
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ("result", "results", "records"):
            value = body.get(key)
            if isinstance(value, list):
                return value
    raise ServiceNowAPIError(
        "expected a JSON array from the API",
        status=response.status,
        body=body,
    )
