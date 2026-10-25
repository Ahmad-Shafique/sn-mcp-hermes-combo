"""Tier 2 - the exact requests the local layer makes.

The saved-query runner and the undo service are the two places where the
server acts on its own memory rather than on a plain request, and the
undo service is the one that can destroy data: it has to apply the exact
inverse of whatever was journalled. A test that only checks "the undo
returned something" will not notice if a DELETE became a POST.

These tests pin the verb, the path and the body of every one of them.
"""

from __future__ import annotations

import pytest

from snowmcp.application.local import (
    CacheService,
    HistoryService,
    KnowledgeService,
    SavedQueryService,
    UndoService,
)
from snowmcp.adapters.store.sqlite import SQLiteStore
from snowmcp.domain.errors import NotFoundError, ValidationError
from snowmcp.domain.storage import JournalEntry

from tests.conftest import FakeGateway, ok, records


@pytest.fixture()
def store():
    """A real in-memory store."""
    return SQLiteStore(":memory:")


class TestSavedQueryContract:
    """A saved query is a query the server can rerun in one call."""

    def test_a_saved_query_is_run_against_its_own_table(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=records({"sys_id": "rec1"}))
        service = SavedQueryService(store, gateway)

        service.save("open incidents", "incident", encoded_query="state=2", limit=25)
        result = service.run("open incidents")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/incident"
        assert call.params["sysparm_query"] == "state=2"
        assert call.params["sysparm_limit"] == "25"
        assert result["name"] == "open incidents"
        assert result["table"] == "incident"
        assert result["count"] == 1

    def test_a_saved_query_with_fields_asks_for_them(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=records({"sys_id": "rec1"}))
        service = SavedQueryService(store, gateway)

        service.save("narrow", "incident", fields=("number", "state"))
        service.run("narrow")

        assert gateway.last().params["sysparm_fields"] == "number,state"

    def test_a_saved_query_with_no_fields_asks_for_none(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=records({"sys_id": "rec1"}))
        service = SavedQueryService(store, gateway)

        service.save("wide", "incident")
        service.run("wide")

        assert "sysparm_fields" not in gateway.last().params

    def test_running_an_unknown_query_is_a_not_found(self, store: SQLiteStore) -> None:
        service = SavedQueryService(store, FakeGateway())

        with pytest.raises(NotFoundError):
            service.run("nope")

    def test_a_saved_query_needs_a_name(self, store: SQLiteStore) -> None:
        service = SavedQueryService(store, FakeGateway())

        with pytest.raises(ValidationError):
            service.save("", "incident")

    def test_a_run_that_returns_a_non_list_result_counts_nothing(
        self, store: SQLiteStore
    ) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "rec1"}}))
        service = SavedQueryService(store, gateway)

        service.save("open", "incident")
        result = service.run("open")

        assert result["count"] == 0
        assert result["records"] == []

    def test_a_run_drops_rows_that_are_not_objects(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": ["not-a-row", {"sys_id": "rec1"}]}))
        service = SavedQueryService(store, gateway)

        service.save("open", "incident")
        result = service.run("open")

        assert result["records"] == [{"sys_id": "rec1"}]

    def test_a_saved_query_is_listed(self, store: SQLiteStore) -> None:
        service = SavedQueryService(store, FakeGateway())

        service.save("one", "incident")
        service.save("two", "change_request")

        assert [query.name for query in service.list()] == ["one", "two"]


class TestUndoContract:
    """Undo applies the exact inverse of the journalled operation."""

    def test_undo_needs_confirmation(self, store: SQLiteStore) -> None:
        service = UndoService(store, FakeGateway())

        with pytest.raises(ValidationError):
            service.undo("e1")

    def test_undoing_an_unknown_entry_is_a_not_found(self, store: SQLiteStore) -> None:
        service = UndoService(store, FakeGateway())

        with pytest.raises(NotFoundError):
            service.undo("nope", confirmed=True)

    def test_undoing_a_create_deletes_the_record(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(entry_id="e1", operation="create", table="incident", sys_id="rec1")
        )

        result = service.undo("e1", confirmed=True)

        call = gateway.last()
        assert call.method == "DELETE"
        assert call.path == "/api/now/table/incident/rec1"
        assert result["reverted"] is True
        assert result["plan"] == "deleted incident/rec1"

    def test_undoing_a_create_with_no_record_id_does_nothing(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(entry_id="e1", operation="create", table="incident", sys_id="")
        )

        result = service.undo("e1", confirmed=True)

        assert gateway.calls == []
        assert result["plan"] == "nothing to delete"

    def test_undoing_an_update_restores_the_previous_fields(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(
                entry_id="e1",
                operation="update",
                table="incident",
                sys_id="rec1",
                before={"state": "1", "short_description": "old"},
            )
        )

        result = service.undo("e1", confirmed=True)

        call = gateway.last()
        assert call.method == "PATCH"
        assert call.path == "/api/now/table/incident/rec1"
        assert call.json_body == {"state": "1", "short_description": "old"}
        assert result["plan"] == "restored previous fields on incident/rec1"

    def test_undoing_an_update_with_no_before_state_does_nothing(
        self, store: SQLiteStore
    ) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(
                entry_id="e1", operation="update", table="incident", sys_id="rec1", before=None
            )
        )

        result = service.undo("e1", confirmed=True)

        assert gateway.calls == []
        assert result["plan"] == "no automatic revert for operation 'update'"

    def test_undoing_a_delete_recreates_the_record(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(
                entry_id="e1",
                operation="delete",
                table="incident",
                sys_id="rec1",
                after={"sys_id": "rec1", "short_description": "gone"},
            )
        )

        result = service.undo("e1", confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/table/incident"
        assert call.json_body == {"sys_id": "rec1", "short_description": "gone"}
        assert result["plan"] == "recreated incident/rec1"

    def test_undoing_a_delete_with_no_after_state_does_nothing(
        self, store: SQLiteStore
    ) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(
                entry_id="e1", operation="delete", table="incident", sys_id="rec1", after=None
            )
        )

        result = service.undo("e1", confirmed=True)

        assert gateway.calls == []
        assert result["plan"] == "no automatic revert for operation 'delete'"

    def test_an_unknown_operation_is_not_reverted(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(entry_id="e1", operation="merge", table="incident", sys_id="rec1")
        )

        result = service.undo("e1", confirmed=True)

        assert gateway.calls == []
        assert result["plan"] == "no automatic revert for operation 'merge'"

    def test_undoing_twice_is_refused(self, store: SQLiteStore) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = UndoService(store, gateway)
        store.journal_append(
            JournalEntry(entry_id="e1", operation="create", table="incident", sys_id="rec1")
        )

        service.undo("e1", confirmed=True)
        result = service.undo("e1", confirmed=True)

        assert result["reverted"] is False
        assert result["reason"] == "already reverted"

    def test_the_journal_is_listed(self, store: SQLiteStore) -> None:
        service = UndoService(store, FakeGateway())
        store.journal_append(
            JournalEntry(entry_id="e1", operation="create", table="incident", sys_id="rec1")
        )

        views = service.list()

        assert [view.entry.entry_id for view in views] == ["e1"]


class TestLocalStoreContract:
    """The local services are pure store operations - no instance calls."""

    def test_a_note_round_trips(self, store: SQLiteStore) -> None:
        gateway = FakeGateway()
        service = KnowledgeService(store)

        service.write("k1", "Title", "body", ["a", "b"])

        note = service.read("k1")
        assert note is not None
        assert note.title == "Title"
        assert gateway.calls == []

    def test_notes_are_searched(self, store: SQLiteStore) -> None:
        service = KnowledgeService(store)
        service.write("k1", "Laptop", "a broken laptop")

        assert [note.key for note in service.search("laptop")] == ["k1"]

    def test_notes_are_listed(self, store: SQLiteStore) -> None:
        service = KnowledgeService(store)
        service.write("k1", "One", "b")
        service.write("k2", "Two", "b")

        assert [note.key for note in service.list()] == ["k1", "k2"]

    def test_a_note_is_deleted(self, store: SQLiteStore) -> None:
        service = KnowledgeService(store)
        service.write("k1", "One", "b")

        assert service.delete("k1") is True
        with pytest.raises(NotFoundError):
            service.read("k1")

    def test_reading_a_note_that_does_not_exist_is_a_not_found(
        self, store: SQLiteStore
    ) -> None:
        service = KnowledgeService(store)

        with pytest.raises(NotFoundError):
            service.read("nope")

    def test_a_cached_record_round_trips(self, store: SQLiteStore) -> None:
        service = CacheService(store)

        service.put("incident", "rec1", {"short_description": "x"})

        cached = service.get("incident", "rec1")
        assert cached is not None
        assert cached.payload == {"short_description": "x"}

    def test_cached_records_are_listed_by_table(self, store: SQLiteStore) -> None:
        service = CacheService(store)
        service.put("incident", "rec1", {"a": 1})
        service.put("incident", "rec2", {"a": 2})
        service.put("change_request", "cr1", {"a": 3})

        assert [item.sys_id for item in service.list("incident")] == ["rec1", "rec2"]

    def test_a_call_is_recorded_in_the_history(self, store: SQLiteStore) -> None:
        service = HistoryService(store)

        service.record("sn_read", "read incident")

        history = service.list()
        assert history[0].tool == "sn_read"
