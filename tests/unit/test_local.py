"""Tier 1 - unit tests for the local storage use cases."""

from __future__ import annotations

import pytest

from snowmcp.application.local import (
    CacheService,
    HistoryService,
    KnowledgeService,
    SavedQueryService,
    UndoService,
)
from snowmcp.application.ports import Response
from snowmcp.domain.errors import NotFoundError, ValidationError
from snowmcp.domain.storage import JournalEntry, SavedQuery

from tests.conftest import FakeGateway, ok, records


def test_a_note_round_trips() -> None:
    store = FakeStore()
    service = KnowledgeService(store)

    note = service.write("runbook", "Runbook", "Steps to recover", ["ops"])

    assert note.key == "runbook"
    assert store.read_note("runbook").body == "Steps to recover"


def test_writing_a_note_without_a_key_is_refused() -> None:
    service = KnowledgeService(FakeStore())

    with pytest.raises(ValidationError, match=r"^note key is required$"):
        service.write("", "Title", "Body")


def test_reading_a_missing_note_raises_not_found() -> None:
    service = KnowledgeService(FakeStore())

    with pytest.raises(NotFoundError, match=r"^no note with key 'nope'$"):
        service.read("nope")


def test_notes_are_searched_by_text() -> None:
    store = FakeStore()
    service = KnowledgeService(store)
    service.write("a", "Alpha", "contains needle")
    service.write("b", "Beta", "nothing here")

    found = service.search("needle")

    assert [note.key for note in found] == ["a"]


def test_notes_are_listed_and_deleted() -> None:
    store = FakeStore()
    service = KnowledgeService(store)
    service.write("a", "Alpha", "body")

    assert len(service.list()) == 1
    assert service.delete("a") is True
    assert service.delete("a") is False


def test_a_cached_record_round_trips() -> None:
    store = FakeStore()
    service = CacheService(store)

    service.put("incident", "abc", {"number": "INC01"})

    assert service.get("incident", "abc").payload["number"] == "INC01"
    assert len(service.list("incident")) == 1


def test_reading_a_missing_cached_record_returns_none() -> None:
    assert CacheService(FakeStore()).get("incident", "nope") is None


def test_a_saved_query_round_trips() -> None:
    store = FakeStore()
    service = SavedQueryService(store, FakeGateway())

    saved = service.save("open-incidents", "incident", encoded_query="state=2")

    assert saved.name == "open-incidents"
    assert service.list()[0].table == "incident"


def test_saving_a_query_without_a_name_is_refused() -> None:
    service = SavedQueryService(FakeStore(), FakeGateway())

    with pytest.raises(ValidationError, match=r"^saved query name is required$"):
        service.save("", "incident")


def test_running_a_saved_query_issues_one_request() -> None:
    gateway = FakeGateway(default=records({"sys_id": "a"}))
    store = FakeStore()
    service = SavedQueryService(store, gateway)
    service.save("open", "incident", encoded_query="state=2")

    result = service.run("open")

    assert len(gateway.calls) == 1
    assert result["count"] == 1


def test_running_a_missing_saved_query_raises_not_found() -> None:
    service = SavedQueryService(FakeStore(), FakeGateway())

    with pytest.raises(NotFoundError, match=r"^no saved query named 'nope'$"):
        service.run("nope")


def test_history_records_and_lists_calls() -> None:
    store = FakeStore()
    service = HistoryService(store)

    service.record("sn_read", "query incident")

    assert service.list()[0].summary == "query incident"


class TestUndo:
    """Reverting an applied write."""

    def test_undo_without_confirmation_is_refused(self) -> None:
        service = UndoService(FakeStore(), FakeGateway())

        with pytest.raises(ValidationError, match=r"^undo requires confirmation: pass confirm=true$"):
            service.undo("create:incident:abc")

    def test_undo_of_an_unknown_entry_raises_not_found(self) -> None:
        service = UndoService(FakeStore(), FakeGateway())

        with pytest.raises(NotFoundError, match=r"^no journal entry with id 'nope'$"):
            service.undo("nope", confirmed=True)

    def test_undoing_a_create_deletes_the_record(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(entry_id="create:incident:abc", operation="create", table="incident", sys_id="abc")
        )
        service = UndoService(store, gateway)

        result = service.undo("create:incident:abc", confirmed=True)

        assert result["reverted"] is True
        assert gateway.last().method == "DELETE"

    def test_undoing_an_update_restores_the_previous_fields(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(
                entry_id="update:incident:abc",
                operation="update",
                table="incident",
                sys_id="abc",
                before={"state": "2"},
            )
        )
        service = UndoService(store, gateway)

        service.undo("update:incident:abc", confirmed=True)

        assert gateway.last().method == "PATCH"
        assert gateway.last().json_body == {"state": "2"}

    def test_undoing_a_delete_recreates_the_record(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(
                entry_id="delete:incident:abc",
                operation="delete",
                table="incident",
                sys_id="abc",
                after={"short_description": "gone"},
            )
        )
        service = UndoService(store, gateway)

        service.undo("delete:incident:abc", confirmed=True)

        assert gateway.last().method == "POST"
        assert gateway.last().json_body == {"short_description": "gone"}

    def test_undoing_an_already_reverted_entry_is_a_no_op(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(
                entry_id="create:incident:abc",
                operation="create",
                table="incident",
                sys_id="abc",
                reverted=True,
            )
        )
        service = UndoService(store, gateway)

        result = service.undo("create:incident:abc", confirmed=True)

        assert result["reverted"] is False
        assert result["reason"] == "already reverted"

    def test_undoing_an_unknown_operation_has_no_plan(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(entry_id="x", operation="frobnicate", table="incident", sys_id="abc")
        )
        service = UndoService(store, gateway)

        result = service.undo("x", confirmed=True)

        assert "no automatic revert" in result["plan"]

    def test_undoing_a_create_without_a_sys_id_does_nothing(self) -> None:
        gateway = FakeGateway(default=ok({}))
        store = FakeStore()
        store.journal_append(
            JournalEntry(entry_id="x", operation="create", table="incident", sys_id="")
        )
        service = UndoService(store, gateway)

        result = service.undo("x", confirmed=True)

        assert result["plan"] == "nothing to delete"


class FakeStore:
    """An in-memory stand-in for the local store."""

    def __init__(self) -> None:
        self.notes: dict[str, object] = {}
        self.cache: dict[tuple[str, str], object] = {}
        self.queries: dict[str, SavedQuery] = {}
        self.calls: list[tuple[str, str]] = []
        self.journal: list[JournalEntry] = []

    def write_note(self, key, title, body, tags):
        from snowmcp.domain.storage import Note

        note = Note(key=key, title=title, body=body, tags=tuple(tags))
        self.notes[key] = note
        return note

    def read_note(self, key):
        return self.notes.get(key)

    def search_notes(self, text):
        needle = text.lower()
        return [
            note
            for note in self.notes.values()
            if needle in note.key.lower() or needle in note.title.lower() or needle in note.body.lower()
        ]

    def list_notes(self):
        return list(self.notes.values())

    def delete_note(self, key):
        return self.notes.pop(key, None) is not None

    def cache_put(self, table, sys_id, payload):
        from snowmcp.domain.storage import CachedRecord

        record = CachedRecord(table=table, sys_id=sys_id, payload=dict(payload))
        self.cache[(table, sys_id)] = record
        return record

    def cache_get(self, table, sys_id):
        return self.cache.get((table, sys_id))

    def cache_list(self, table):
        return [record for (name, _), record in self.cache.items() if name == table]

    def save_query(self, query):
        self.queries[query.name] = query
        return query

    def get_query(self, name):
        return self.queries.get(name)

    def list_queries(self):
        return list(self.queries.values())

    def record_call(self, tool, summary):
        from snowmcp.domain.storage import CallRecord

        call = CallRecord(tool=tool, summary=summary)
        self.calls.append((tool, summary))
        return call

    def history(self, limit=50):
        from snowmcp.domain.storage import CallRecord

        return [CallRecord(tool=tool, summary=summary) for tool, summary in reversed(self.calls[-limit:])]

    def journal_append(self, entry):
        self.journal.append(entry)
        return entry

    def journal_list(self, limit=50):
        from snowmcp.domain.storage import JournalView

        return [JournalView(entry=entry) for entry in reversed(self.journal[-limit:])]

    def journal_mark_reverted(self, entry_id):
        import dataclasses

        for index, entry in enumerate(self.journal):
            if entry.entry_id == entry_id:
                self.journal[index] = dataclasses.replace(entry, reverted=True)
                return True
        return False
