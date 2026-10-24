"""Local storage use cases: notes, cache, saved queries, history, undo.

This is the half of the server that never touches the instance. It exists so
the agent can *store* what it learns, so a second look-up costs no API call,
and so a write can be taken back.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from snowmcp.application.ports import (
    CallHistory,
    InstanceGateway,
    KnowledgeStore,
    QueryLibrary,
    RecordCache,
    WriteJournal,
)
from snowmcp.application.responses import unwrap_records
from snowmcp.domain.errors import NotFoundError, ValidationError
from snowmcp.domain.records import Query
from snowmcp.domain.storage import (
    CachedRecord,
    CallRecord,
    JournalEntry,
    JournalView,
    Note,
    SavedQuery,
    tags_from,
)


class KnowledgeService:
    """The local markdown knowledge base."""

    def __init__(self, store: KnowledgeStore) -> None:
        self._store = store

    def write(self, key: str, title: str, body: str, tags: Sequence[str] | str | None = None) -> Note:
        """Create or replace a note."""
        if not key:
            raise ValidationError("note key is required")
        return self._store.write_note(key, title or key, body or "", tags_from(tags))

    def read(self, key: str) -> Note:
        """Read a note."""
        note = self._store.read_note(key)
        if note is None:
            raise NotFoundError(f"no note with key {key!r}")
        return note

    def search(self, text: str) -> list[Note]:
        """Search notes by text."""
        return self._store.search_notes(text)

    def list(self) -> list[Note]:
        """List every note."""
        return self._store.list_notes()

    def delete(self, key: str) -> bool:
        """Delete a note."""
        return self._store.delete_note(key)


class CacheService:
    """The local record cache."""

    def __init__(self, store: RecordCache) -> None:
        self._store = store

    def put(self, table: str, sys_id: str, payload: Mapping[str, Any]) -> CachedRecord:
        """Store a record locally."""
        return self._store.cache_put(table, sys_id, payload)

    def get(self, table: str, sys_id: str) -> CachedRecord | None:
        """Read a record from the local cache."""
        return self._store.cache_get(table, sys_id)

    def list(self, table: str) -> list[CachedRecord]:
        """List cached records for a table."""
        return self._store.cache_list(table)


class SavedQueryService:
    """Named, reusable queries."""

    def __init__(self, library: QueryLibrary, gateway: InstanceGateway) -> None:
        self._library = library
        self._gateway = gateway

    def save(
        self,
        name: str,
        table: str,
        *,
        encoded_query: str = "",
        fields: Sequence[str] = (),
        limit: int = 100,
    ) -> SavedQuery:
        """Store a named query."""
        if not name:
            raise ValidationError("saved query name is required")
        query = SavedQuery(
            name=name,
            table=table,
            encoded_query=encoded_query,
            fields=tuple(fields),
            limit=limit,
        )
        return self._library.save_query(query)

    def list(self) -> list[SavedQuery]:
        """List saved queries."""
        return self._library.list_queries()

    def run(self, name: str) -> dict[str, Any]:
        """Run a saved query, in one call."""
        query = self._library.get_query(name)
        if query is None:
            raise NotFoundError(f"no saved query named {name!r}")
        response = self._gateway.request(
            "GET",
            f"/api/now/table/{query.table}",
            params={
                "sysparm_query": query.encoded_query,
                "sysparm_limit": str(query.limit),
                **({"sysparm_fields": ",".join(query.fields)} if query.fields else {}),
            },
        )
        body = unwrap_records(response)
        result = body.get("result")
        records = [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        return {"name": name, "table": query.table, "count": len(records), "records": records}


class HistoryService:
    """What the agent already did."""

    def __init__(self, history: CallHistory) -> None:
        self._history = history

    def record(self, tool: str, summary: str) -> CallRecord:
        """Record a completed call."""
        return self._history.record_call(tool, summary)

    def list(self, limit: int = 50) -> list[CallRecord]:
        """Read the call history."""
        return self._history.history(limit)


class UndoService:
    """Revert an applied write."""

    def __init__(self, journal: WriteJournal, gateway: InstanceGateway) -> None:
        self._journal = journal
        self._gateway = gateway

    def list(self, limit: int = 50) -> list[JournalView]:
        """List applied writes with the plan for reverting each."""
        return self._journal.journal_list(limit)

    def undo(self, entry_id: str, *, confirmed: bool = False) -> dict[str, Any]:
        """Revert one journalled write."""
        if not confirmed:
            raise ValidationError("undo requires confirmation: pass confirm=true")
        view = next((item for item in self._journal.journal_list(200) if item.entry.entry_id == entry_id), None)
        if view is None:
            raise NotFoundError(f"no journal entry with id {entry_id!r}")
        entry = view.entry
        if entry.reverted:
            return {"entry_id": entry_id, "reverted": False, "reason": "already reverted"}
        plan = self._revert(entry)
        self._journal.journal_mark_reverted(entry_id)
        return {"entry_id": entry_id, "reverted": True, "plan": plan}

    def _revert(self, entry: JournalEntry) -> str:
        """Apply the inverse of a journalled operation."""
        if entry.operation == "create":
            if entry.sys_id:
                self._gateway.request("DELETE", f"/api/now/table/{entry.table}/{entry.sys_id}")
                return f"deleted {entry.table}/{entry.sys_id}"
            return "nothing to delete"
        if entry.operation == "update" and entry.before is not None:
            self._gateway.request(
                "PATCH",
                f"/api/now/table/{entry.table}/{entry.sys_id}",
                json_body=dict(entry.before),
            )
            return f"restored previous fields on {entry.table}/{entry.sys_id}"
        if entry.operation == "delete" and entry.after is not None:
            self._gateway.request(
                "POST", f"/api/now/table/{entry.table}", json_body=dict(entry.after)
            )
            return f"recreated {entry.table}/{entry.sys_id}"
        return f"no automatic revert for operation {entry.operation!r}"
