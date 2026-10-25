"""Tier 2 - what a batch writes to the journal.

A batch is the one place where several writes happen inside one request,
and every one of them is journalled so it can be reverted. The journal
entry is therefore the only place the per-operation details are
observable: which verb was treated as a write, which table it named, and
which record it touched.

Without these assertions, a batch that quietly stopped journalling a
``PUT`` or a ``DELETE``, or journalled the wrong table, would look
identical from the outside - the instance would still have been written
to correctly.
"""

from __future__ import annotations

from typing import Any

from snowmcp.application.ports import Response
from snowmcp.application.records import RecordService
import pytest

from snowmcp.domain.errors import JournalWriteError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.storage import JournalEntry, JournalView

from tests.conftest import FakeGateway, ok


class RecordingJournal:
    """A journal that keeps what it was told."""

    def __init__(self) -> None:
        self.entries: list[JournalEntry] = []

    def journal_append(self, entry: JournalEntry) -> JournalEntry:
        self.entries.append(entry)
        return entry

    def journal_list(self, limit: int = 50) -> list[JournalView]:
        return [JournalView(entry=entry) for entry in self.entries[:limit]]

    def journal_mark_reverted(self, entry_id: str) -> bool:
        return True


def service(journal: RecordingJournal | None = None) -> RecordService:
    """A record service writing to a recording journal."""
    return RecordService(
        FakeGateway(default=ok({"result": []})),
        WritePolicy(require_confirm=False),
        journal=journal,
    )


class TestBatchJournal:
    """Each write in a batch leaves one journal entry."""

    def test_a_post_is_journalled_as_a_create(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "POST", "table": "incident", "body": {"short_description": "x"}}]
        )

        assert len(journal.entries) == 1
        assert journal.entries[0].operation == "post"
        assert journal.entries[0].table == "incident"

    def test_a_patch_is_journalled_as_a_patch(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "PATCH", "table": "incident", "body": {"short_description": "x"}}]
        )

        assert journal.entries[0].operation == "patch"

    def test_a_put_is_journalled_as_a_put(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "PUT", "table": "incident", "body": {"short_description": "x"}}]
        )

        # A PUT is a write. If the verb list lost "PUT" the entry would
        # never be written, and the write could never be reverted.
        assert len(journal.entries) == 1
        assert journal.entries[0].operation == "put"

    def test_a_delete_is_journalled_as_a_delete(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "DELETE", "table": "incident", "body": {"short_description": "x"}}]
        )

        # A DELETE is a write, and the one whose loss matters most.
        assert len(journal.entries) == 1
        assert journal.entries[0].operation == "delete"

    def test_a_get_is_not_journalled(self) -> None:
        journal = RecordingJournal()

        service(journal).batch([{"method": "GET", "table": "incident"}])

        assert journal.entries == []

    def test_an_operation_with_no_method_is_not_journalled(self) -> None:
        journal = RecordingJournal()

        service(journal).batch([{"table": "incident"}])

        # An absent method is not a write verb, so nothing is journalled.
        assert journal.entries == []

    def test_the_journalled_table_is_the_operations_table(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "POST", "table": "change_request", "body": {"x": 1}}]
        )

        assert journal.entries[0].table == "change_request"

    def test_an_operation_with_no_table_journals_an_empty_table(self) -> None:
        journal = RecordingJournal()

        service(journal).batch([{"method": "POST", "body": {"x": 1}}])

        assert journal.entries[0].table == ""

    def test_the_journalled_record_is_the_one_in_the_body(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "POST", "table": "incident", "body": {"sys_id": "rec1"}}]
        )

        assert journal.entries[0].sys_id == "rec1"

    def test_a_body_with_no_sys_id_journals_an_empty_record(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "POST", "table": "incident", "body": {"short_description": "x"}}]
        )

        assert journal.entries[0].sys_id == ""

    def test_a_body_that_is_not_a_mapping_journals_an_empty_record(self) -> None:
        journal = RecordingJournal()

        service(journal).batch([{"method": "POST", "table": "incident", "body": "not-a-mapping"}])

        assert journal.entries[0].sys_id == ""

    def test_an_operation_with_no_body_journals_an_empty_body(self) -> None:
        journal = RecordingJournal()

        service(journal).batch([{"method": "POST", "table": "incident"}])

        assert journal.entries[0].after == {}

    def test_each_write_in_the_batch_gets_its_own_entry(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [
                {"method": "POST", "table": "incident", "body": {"sys_id": "a"}},
                {"method": "DELETE", "table": "incident", "body": {"sys_id": "b"}},
            ]
        )

        assert [entry.operation for entry in journal.entries] == ["post", "delete"]
        assert [entry.sys_id for entry in journal.entries] == ["a", "b"]

    def test_the_entry_id_names_the_operation_the_table_and_the_record(self) -> None:
        journal = RecordingJournal()

        service(journal).batch(
            [{"method": "POST", "table": "incident", "body": {"sys_id": "rec1"}}]
        )

        assert journal.entries[0].entry_id == "post:incident:rec1"


class TestSingleWriteJournal:
    """The same journal contract for a single write."""

    def test_a_create_is_journalled_with_the_new_fields(self) -> None:
        journal = RecordingJournal()
        gateway = FakeGateway(default=ok({"result": {"sys_id": "rec1"}}))

        RecordService(gateway, WritePolicy(require_confirm=False), journal=journal).create(
            "incident", {"short_description": "x"}
        )

        assert journal.entries[0].operation == "create"
        assert journal.entries[0].table == "incident"
        assert journal.entries[0].sys_id == "rec1"
        assert journal.entries[0].before is None
        assert journal.entries[0].after == {"sys_id": "rec1"}

    def test_an_update_journals_the_previous_fields(self) -> None:
        journal = RecordingJournal()
        gateway = FakeGateway(
            responses={"/api/now/table/incident/s1": ok({"result": {"sys_id": "s1", "state": "1"}})}
        )

        RecordService(gateway, WritePolicy(require_confirm=False), journal=journal).update(
            "incident", "s1", {"state": "2"}
        )

        assert journal.entries[0].operation == "update"
        assert journal.entries[0].before == {"result": {"sys_id": "s1", "state": "1"}}

    def test_a_delete_journals_the_previous_fields(self) -> None:
        journal = RecordingJournal()
        gateway = FakeGateway(
            responses={"/api/now/table/incident/s1": ok({"result": {"sys_id": "s1"}})}
        )

        RecordService(gateway, WritePolicy(require_confirm=False), journal=journal).delete(
            "incident", "s1"
        )

        assert journal.entries[0].operation == "delete"
        assert journal.entries[0].after is None

    def test_a_write_with_no_journal_is_still_performed(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "rec1"}}))

        record = RecordService(gateway, WritePolicy(require_confirm=False)).create(
            "incident", {"short_description": "x"}
        )

        assert record.sys_id == "rec1"

    def test_a_failed_journal_write_says_the_write_reached_the_instance(self) -> None:
        class BrokenJournal(RecordingJournal):
            def journal_append(self, entry: JournalEntry) -> JournalEntry:
                raise RuntimeError("journal is down")

        gateway = FakeGateway(default=ok({"result": {"sys_id": "rec1"}}))

        # The write reached the instance. The error has to say so,
        # otherwise a caller that retries creates a duplicate record.
        with pytest.raises(JournalWriteError) as caught:
            RecordService(
                gateway, WritePolicy(require_confirm=False), journal=BrokenJournal()
            ).create("incident", {"short_description": "x"})

        message = str(caught.value)
        assert "reached the instance" in message
        assert "cannot be reverted" in message
        assert "journal is down" in message
