"""Tier 2 - integration tests. The real SQLite store, for real.

The unit tests use an in-memory fake; these exercise the actual SQL, so a
mistake in the schema or a query shows up here rather than in production.
"""

from __future__ import annotations

import pytest

from snowmcp.adapters.store.sqlite import SQLiteStore
from snowmcp.domain.storage import JournalEntry, SavedQuery


@pytest.fixture
def file_store(tmp_path) -> SQLiteStore:
    """A store backed by a real file on disk."""
    return SQLiteStore(tmp_path / "store.sqlite3")


def test_the_schema_is_created_on_a_fresh_file(tmp_path) -> None:
    path = tmp_path / "nested" / "store.sqlite3"
    store = SQLiteStore(path)

    assert path.exists()
    store.close()


def test_a_note_is_written_and_read_back(file_store: SQLiteStore) -> None:
    file_store.write_note("runbook", "Runbook", "Steps to recover", ("ops", "oncall"))

    note = file_store.read_note("runbook")

    assert note is not None
    assert note.title == "Runbook"
    assert note.body == "Steps to recover"
    assert note.tags == ("ops", "oncall")


def test_writing_a_note_twice_replaces_it(file_store: SQLiteStore) -> None:
    file_store.write_note("runbook", "Runbook", "first", ())
    file_store.write_note("runbook", "Runbook", "second", ())

    assert file_store.read_note("runbook").body == "second"


def test_reading_a_missing_note_returns_none(file_store: SQLiteStore) -> None:
    assert file_store.read_note("nope") is None


def test_notes_are_searched_across_every_field(file_store: SQLiteStore) -> None:
    file_store.write_note("a", "Alpha", "contains needle", ("tagged",))
    file_store.write_note("b", "Beta", "nothing", ("other",))

    assert [note.key for note in file_store.search_notes("needle")] == ["a"]
    assert [note.key for note in file_store.search_notes("tagged")] == ["a"]
    assert [note.key for note in file_store.search_notes("beta")] == ["b"]


def test_notes_are_listed_in_key_order(file_store: SQLiteStore) -> None:
    file_store.write_note("b", "Beta", "", ())
    file_store.write_note("a", "Alpha", "", ())

    assert [note.key for note in file_store.list_notes()] == ["a", "b"]


def test_deleting_a_note_reports_whether_it_existed(file_store: SQLiteStore) -> None:
    file_store.write_note("a", "Alpha", "", ())

    assert file_store.delete_note("a") is True
    assert file_store.delete_note("a") is False


def test_a_record_is_cached_and_read_back(file_store: SQLiteStore) -> None:
    file_store.cache_put("incident", "abc", {"number": "INC01"})

    cached = file_store.cache_get("incident", "abc")

    assert cached is not None
    assert cached.payload["number"] == "INC01"


def test_caching_a_record_twice_refreshes_it(file_store: SQLiteStore) -> None:
    file_store.cache_put("incident", "abc", {"number": "INC01"})
    file_store.cache_put("incident", "abc", {"number": "INC02"})

    assert file_store.cache_get("incident", "abc").payload["number"] == "INC02"


def test_reading_a_missing_cached_record_returns_none(file_store: SQLiteStore) -> None:
    assert file_store.cache_get("incident", "nope") is None


def test_cached_records_are_listed_per_table(file_store: SQLiteStore) -> None:
    file_store.cache_put("incident", "a", {})
    file_store.cache_put("incident", "b", {})
    file_store.cache_put("change_request", "c", {})

    assert len(file_store.cache_list("incident")) == 2
    assert len(file_store.cache_list("change_request")) == 1


def test_a_saved_query_round_trips(file_store: SQLiteStore) -> None:
    file_store.save_query(
        SavedQuery(name="open", table="incident", encoded_query="state=2", fields=("number",))
    )

    query = file_store.get_query("open")

    assert query is not None
    assert query.table == "incident"
    assert query.fields == ("number",)


def test_saving_a_query_twice_replaces_it(file_store: SQLiteStore) -> None:
    file_store.save_query(SavedQuery(name="open", table="incident", limit=10))
    file_store.save_query(SavedQuery(name="open", table="incident", limit=99))

    assert file_store.get_query("open").limit == 99


def test_reading_a_missing_saved_query_returns_none(file_store: SQLiteStore) -> None:
    assert file_store.get_query("nope") is None


def test_saved_queries_are_listed(file_store: SQLiteStore) -> None:
    file_store.save_query(SavedQuery(name="a", table="incident"))
    file_store.save_query(SavedQuery(name="b", table="incident"))

    assert [query.name for query in file_store.list_queries()] == ["a", "b"]


def test_the_call_history_records_and_lists_in_reverse_order(file_store: SQLiteStore) -> None:
    file_store.record_call("sn_read", "first")
    file_store.record_call("sn_read", "second")

    history = file_store.history()

    assert [call.summary for call in history] == ["second", "first"]


def test_the_call_history_is_bounded(file_store: SQLiteStore) -> None:
    for index in range(5):
        file_store.record_call("sn_read", f"call {index}")

    assert len(file_store.history(limit=2)) == 2


def test_a_journalled_write_is_listed_with_a_revert_plan(file_store: SQLiteStore) -> None:
    file_store.journal_append(
        JournalEntry(
            entry_id="create:incident:abc",
            operation="create",
            table="incident",
            sys_id="abc",
        )
    )

    views = file_store.journal_list()

    assert views[0].entry.entry_id == "create:incident:abc"
    assert views[0].plan == "delete incident/abc"


def test_the_revert_plan_covers_every_operation(file_store: SQLiteStore) -> None:
    file_store.journal_append(
        JournalEntry(entry_id="u", operation="update", table="incident", sys_id="abc")
    )
    file_store.journal_append(
        JournalEntry(entry_id="d", operation="delete", table="incident", sys_id="abc")
    )
    file_store.journal_append(
        JournalEntry(entry_id="x", operation="frobnicate", table="incident", sys_id="abc")
    )

    plans = {view.entry.entry_id: view.plan for view in file_store.journal_list()}

    assert plans["u"] == "restore the previous fields on incident/abc"
    assert plans["d"] == "recreate incident/abc"
    assert "no automatic revert" in plans["x"]


def test_a_reverted_entry_says_so(file_store: SQLiteStore) -> None:
    file_store.journal_append(
        JournalEntry(entry_id="x", operation="create", table="incident", sys_id="abc")
    )
    file_store.journal_mark_reverted("x")

    assert file_store.journal_list()[0].plan == "already reverted"


def test_marking_a_missing_entry_reports_false(file_store: SQLiteStore) -> None:
    assert file_store.journal_mark_reverted("nope") is False


def test_the_journal_survives_a_reopen(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    first = SQLiteStore(path)
    first.write_note("runbook", "Runbook", "body", ())
    first.close()

    second = SQLiteStore(path)

    assert second.read_note("runbook").body == "body"


def test_a_corrupt_cached_payload_reads_as_empty(file_store: SQLiteStore) -> None:
    file_store._connection.execute(
        "INSERT INTO cache (table_name, sys_id, payload, fetched_at) VALUES (?, ?, ?, ?)",
        ("incident", "abc", "not json", "2026-01-01T00:00:00+00:00"),
    )
    file_store._connection.commit()

    assert file_store.cache_get("incident", "abc").payload == {}
