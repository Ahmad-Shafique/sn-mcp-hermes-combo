"""Outbound ports.

Each protocol is deliberately small: a use case depends only on what it
actually needs, never on a fat "repository" interface it would ignore half of.
That is the Interface Segregation Principle applied to ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from snowmcp.domain.storage import (
    CachedRecord,
    CallRecord,
    JournalEntry,
    JournalView,
    Note,
    SavedQuery,
)


@dataclass(frozen=True)
class Response:
    """A raw response from the instance, before any domain interpretation."""

    status: int
    body: Any = None
    headers: Mapping[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class InstanceGateway(Protocol):
    """Transport to a ServiceNow instance. The only outbound network port."""

    def request(self, method: str, path: str, params=None, json_body=None, headers=None) -> Response: ...


class KnowledgeStore(Protocol):
    """Local markdown knowledge base."""

    def write_note(self, key: str, title: str, body: str, tags: Sequence[str]) -> Note: ...

    def read_note(self, key: str) -> Note | None: ...

    def search_notes(self, text: str) -> list[Note]: ...

    def list_notes(self) -> list[Note]: ...

    def delete_note(self, key: str) -> bool: ...


class RecordCache(Protocol):
    """Local copy of records already fetched, so repeat lookups cost nothing."""

    def cache_put(self, table: str, sys_id: str, payload: Mapping[str, Any]) -> CachedRecord: ...

    def cache_get(self, table: str, sys_id: str) -> CachedRecord | None: ...

    def cache_list(self, table: str) -> list[CachedRecord]: ...


class QueryLibrary(Protocol):
    """Named, reusable queries."""

    def save_query(self, query: SavedQuery) -> SavedQuery: ...

    def get_query(self, name: str) -> SavedQuery | None: ...

    def list_queries(self) -> list[SavedQuery]: ...


class CallHistory(Protocol):
    """What the agent already did, so it does not do it twice."""

    def record_call(self, tool: str, summary: str) -> CallRecord: ...

    def history(self, limit: int = 50) -> list[CallRecord]: ...


class WriteJournal(Protocol):
    """Applied writes, so they can be reverted."""

    def journal_append(self, entry: JournalEntry) -> JournalEntry: ...

    def journal_list(self, limit: int = 50) -> list[JournalView]: ...

    def journal_mark_reverted(self, entry_id: str) -> bool: ...
