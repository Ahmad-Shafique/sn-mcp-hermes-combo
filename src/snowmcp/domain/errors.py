"""Domain errors. Innermost layer: no imports outward, no framework types."""

from __future__ import annotations

from typing import Any


class SnowMCPError(Exception):
    """Base for every error this server raises deliberately."""


class ConfigurationError(SnowMCPError):
    """The instance URL or credentials are missing or malformed."""


class AuthenticationError(SnowMCPError):
    """The instance rejected the supplied credentials."""


class PermissionDeniedError(SnowMCPError):
    """The identity lacks the ACL needed for this operation."""


class NotFoundError(SnowMCPError):
    """The requested record, table or artifact does not exist."""


class ValidationError(SnowMCPError):
    """The request was malformed before it ever reached the instance."""


class SafetyGuardError(SnowMCPError):
    """A safety control (read-only mode, allow/deny list) refused the call."""


class JournalWriteError(SnowMCPError):
    """The write reached the instance but could not be journalled.

    The record *was* created or changed. What failed is the local
    journal entry that would have made it revertible. Saying so plainly
    matters: a caller that reads this as "the write failed" will retry,
    and a retry creates a duplicate.
    """


class ServiceNowAPIError(SnowMCPError):
    """The ServiceNow REST API answered with an error.

    ``str(error)`` is exactly the message, so tests can assert it verbatim.
    The HTTP status and the raw body stay available as attributes.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        detail: str | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail
        self.body = body
