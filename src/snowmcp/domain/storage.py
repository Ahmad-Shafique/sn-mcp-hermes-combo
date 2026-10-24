"""Local storage value objects: notes, cached records, saved queries, journal.

These model what the server remembers between calls, which is what turns a
stateless REST proxy into a tool that can *store* data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Note:
    """A markdown note in the local knowledge base."""

    key: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class CachedRecord:
    """A ServiceNow record held locally, with the moment it was fetched."""

    table: str
    sys_id: str
    payload: Mapping[str, Any]
    fetched_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "sys_id": self.sys_id,
            "payload": dict(self.payload),
            "fetched_at": self.fetched_at,
        }


@dataclass(frozen=True)
class SavedQuery:
    """A named, reusable query so the same lookup is one call, not ten."""

    name: str
    table: str
    encoded_query: str = ""
    fields: tuple[str, ...] = ()
    limit: int = 100
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table": self.table,
            "encoded_query": self.encoded_query,
            "fields": list(self.fields),
            "limit": self.limit,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CallRecord:
    """One completed call, kept so the agent can see what it already did."""

    tool: str
    summary: str
    at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "summary": self.summary, "at": self.at}


@dataclass(frozen=True)
class JournalEntry:
    """A write that was applied, so it can be reverted."""

    entry_id: str
    operation: str
    table: str
    sys_id: str
    before: Mapping[str, Any] | None = None
    after: Mapping[str, Any] | None = None
    at: str = field(default_factory=_now)
    reverted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "operation": self.operation,
            "table": self.table,
            "sys_id": self.sys_id,
            "before": dict(self.before) if self.before is not None else None,
            "after": dict(self.after) if self.after is not None else None,
            "at": self.at,
            "reverted": self.reverted,
        }


@dataclass(frozen=True)
class JournalView:
    """A journal entry plus what reverting it would do."""

    entry: JournalEntry
    plan: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"entry": self.entry.to_dict(), "plan": self.plan}


def json_dumps(value: Any) -> str:
    """Serialise a payload for storage in a text column."""
    return json.dumps(value, sort_keys=True, default=str)


def json_loads(raw: str | None) -> Any:
    """Read a stored payload back, tolerating an absent or corrupt value."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def tags_from(value: Sequence[str] | str | None) -> tuple[str, ...]:
    """Normalise a tag input into a clean, ordered tuple."""
    if value is None:
        return ()
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    else:
        parts = [str(part).strip() for part in value]
    return tuple(dict.fromkeys(part for part in parts if part))
