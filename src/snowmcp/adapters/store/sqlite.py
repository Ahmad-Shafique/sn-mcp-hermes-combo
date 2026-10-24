"""SQLite-backed local storage.

One file holds the knowledge base, the record cache, saved queries, the call
history and the write journal. SQLite is stdlib, so the server keeps a single
dependency (the MCP SDK) instead of pulling in a database driver.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from snowmcp.domain.storage import (
    CachedRecord,
    CallRecord,
    JournalEntry,
    JournalView,
    Note,
    SavedQuery,
    json_dumps,
    json_loads,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache (
    table_name TEXT NOT NULL,
    sys_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (table_name, sys_id)
);
CREATE TABLE IF NOT EXISTS saved_queries (
    name TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    encoded_query TEXT NOT NULL DEFAULT '',
    fields TEXT NOT NULL DEFAULT '',
    row_limit INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    summary TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal (
    entry_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    table_name TEXT NOT NULL,
    sys_id TEXT NOT NULL,
    before TEXT,
    after TEXT,
    at TEXT NOT NULL,
    reverted INTEGER NOT NULL DEFAULT 0
);
"""


class SQLiteStore:
    """Implements every local-storage port over one SQLite file."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        """Close the underlying connection."""
        self._connection.close()

    # -- KnowledgeStore ----------------------------------------------------

    def write_note(self, key: str, title: str, body: str, tags: Sequence[str]) -> Note:
        """Create or replace a note."""
        existing = self.read_note(key)
        updated_at = existing.updated_at if existing else _now()
        self._connection.execute(
            "INSERT INTO notes (key, title, body, tags, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET title=excluded.title, body=excluded.body, "
            "tags=excluded.tags, updated_at=excluded.updated_at",
            (key, title, body, ",".join(tags), updated_at),
        )
        self._connection.commit()
        return Note(key=key, title=title, body=body, tags=tuple(tags), updated_at=updated_at)

    def read_note(self, key: str) -> Note | None:
        """Read one note."""
        row = self._connection.execute(
            "SELECT key, title, body, tags, updated_at FROM notes WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_note(row)

    def search_notes(self, text: str) -> list[Note]:
        """Find notes whose key, title, body or tags contain the text."""
        needle = f"%{text.lower()}%"
        rows = self._connection.execute(
            "SELECT key, title, body, tags, updated_at FROM notes "
            "WHERE lower(key) LIKE ? OR lower(title) LIKE ? OR lower(body) LIKE ? OR lower(tags) LIKE ? "
            "ORDER BY key",
            (needle, needle, needle, needle),
        ).fetchall()
        return [_row_to_note(row) for row in rows]

    def list_notes(self) -> list[Note]:
        """List every note."""
        rows = self._connection.execute(
            "SELECT key, title, body, tags, updated_at FROM notes ORDER BY key"
        ).fetchall()
        return [_row_to_note(row) for row in rows]

    def delete_note(self, key: str) -> bool:
        """Delete a note, reporting whether it existed."""
        cursor = self._connection.execute("DELETE FROM notes WHERE key = ?", (key,))
        self._connection.commit()
        return cursor.rowcount > 0

    # -- RecordCache -------------------------------------------------------

    def cache_put(self, table: str, sys_id: str, payload: Mapping[str, Any]) -> CachedRecord:
        """Store a record in the local cache."""
        fetched = _now()
        self._connection.execute(
            "INSERT INTO cache (table_name, sys_id, payload, fetched_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(table_name, sys_id) DO UPDATE SET payload=excluded.payload, "
            "fetched_at=excluded.fetched_at",
            (table, sys_id, json_dumps(dict(payload)), fetched),
        )
        self._connection.commit()
        return CachedRecord(table=table, sys_id=sys_id, payload=dict(payload), fetched_at=fetched)

    def cache_get(self, table: str, sys_id: str) -> CachedRecord | None:
        """Read a cached record."""
        row = self._connection.execute(
            "SELECT table_name, sys_id, payload, fetched_at FROM cache "
            "WHERE table_name = ? AND sys_id = ?",
            (table, sys_id),
        ).fetchone()
        if row is None:
            return None
        payload = json_loads(row["payload"]) or {}
        return CachedRecord(
            table=row["table_name"],
            sys_id=row["sys_id"],
            payload=payload if isinstance(payload, dict) else {},
            fetched_at=row["fetched_at"],
        )

    def cache_list(self, table: str) -> list[CachedRecord]:
        """List cached records for one table."""
        rows = self._connection.execute(
            "SELECT table_name, sys_id, payload, fetched_at FROM cache "
            "WHERE table_name = ? ORDER BY fetched_at DESC",
            (table,),
        ).fetchall()
        records = []
        for row in rows:
            payload = json_loads(row["payload"]) or {}
            records.append(
                CachedRecord(
                    table=row["table_name"],
                    sys_id=row["sys_id"],
                    payload=payload if isinstance(payload, dict) else {},
                    fetched_at=row["fetched_at"],
                )
            )
        return records

    # -- QueryLibrary ------------------------------------------------------

    def save_query(self, query: SavedQuery) -> SavedQuery:
        """Store a named query, replacing any earlier one with the same name."""
        self._connection.execute(
            "INSERT INTO saved_queries (name, table_name, encoded_query, fields, row_limit, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET "
            "table_name=excluded.table_name, encoded_query=excluded.encoded_query, "
            "fields=excluded.fields, row_limit=excluded.row_limit",
            (
                query.name,
                query.table,
                query.encoded_query,
                ",".join(query.fields),
                query.limit,
                query.created_at,
            ),
        )
        self._connection.commit()
        return query

    def get_query(self, name: str) -> SavedQuery | None:
        """Read a saved query."""
        row = self._connection.execute(
            "SELECT name, table_name, encoded_query, fields, row_limit, created_at "
            "FROM saved_queries WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_query(row)

    def list_queries(self) -> list[SavedQuery]:
        """List saved queries."""
        rows = self._connection.execute(
            "SELECT name, table_name, encoded_query, fields, row_limit, created_at "
            "FROM saved_queries ORDER BY name"
        ).fetchall()
        return [_row_to_query(row) for row in rows]

    # -- CallHistory -------------------------------------------------------

    def record_call(self, tool: str, summary: str) -> CallRecord:
        """Record a completed call."""
        at = _now()
        self._connection.execute(
            "INSERT INTO history (tool, summary, at) VALUES (?, ?, ?)", (tool, summary, at)
        )
        self._connection.commit()
        return CallRecord(tool=tool, summary=summary, at=at)

    def history(self, limit: int = 50) -> list[CallRecord]:
        """Read the most recent calls."""
        rows = self._connection.execute(
            "SELECT tool, summary, at FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [CallRecord(tool=row["tool"], summary=row["summary"], at=row["at"]) for row in rows]

    # -- WriteJournal ------------------------------------------------------

    def journal_append(self, entry: JournalEntry) -> JournalEntry:
        """Record an applied write."""
        self._connection.execute(
            "INSERT INTO journal (entry_id, operation, table_name, sys_id, before, after, at, reverted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(entry_id) DO NOTHING",
            (
                entry.entry_id,
                entry.operation,
                entry.table,
                entry.sys_id,
                json_dumps(entry.before) if entry.before is not None else None,
                json_dumps(entry.after) if entry.after is not None else None,
                entry.at,
                1 if entry.reverted else 0,
            ),
        )
        self._connection.commit()
        return entry

    def journal_list(self, limit: int = 50) -> list[JournalView]:
        """List applied writes with the plan for reverting each."""
        rows = self._connection.execute(
            "SELECT entry_id, operation, table_name, sys_id, before, after, at, reverted "
            "FROM journal ORDER BY at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
        views = []
        for row in rows:
            entry = JournalEntry(
                entry_id=row["entry_id"],
                operation=row["operation"],
                table=row["table_name"],
                sys_id=row["sys_id"],
                before=json_loads(row["before"]),
                after=json_loads(row["after"]),
                at=row["at"],
                reverted=bool(row["reverted"]),
            )
            views.append(JournalView(entry=entry, plan=_revert_plan(entry)))
        return views

    def journal_mark_reverted(self, entry_id: str) -> bool:
        """Mark an entry as reverted, reporting whether it was there."""
        cursor = self._connection.execute(
            "UPDATE journal SET reverted = 1 WHERE entry_id = ?", (entry_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_note(row: sqlite3.Row) -> Note:
    tags = tuple(tag for tag in (row["tags"] or "").split(",") if tag)
    return Note(
        key=row["key"],
        title=row["title"],
        body=row["body"],
        tags=tags,
        updated_at=row["updated_at"],
    )


def _row_to_query(row: sqlite3.Row) -> SavedQuery:
    fields = tuple(field for field in (row["fields"] or "").split(",") if field)
    return SavedQuery(
        name=row["name"],
        table=row["table_name"],
        encoded_query=row["encoded_query"],
        fields=fields,
        limit=int(row["row_limit"]),
        created_at=row["created_at"],
    )


def _revert_plan(entry: JournalEntry) -> str:
    """Describe what reverting an entry would do."""
    if entry.reverted:
        return "already reverted"
    if entry.operation == "create":
        return f"delete {entry.table}/{entry.sys_id}"
    if entry.operation == "update":
        return f"restore the previous fields on {entry.table}/{entry.sys_id}"
    if entry.operation == "delete":
        return f"recreate {entry.table}/{entry.sys_id}"
    return f"no automatic revert for {entry.operation!r}"
