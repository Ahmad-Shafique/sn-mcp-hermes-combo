"""Tier 1 - unit tests that close the remaining behavioural branches.

Each test here pins a specific edge the code takes: a limit reached, a
response that is not ok, a value of an unexpected shape.
"""

from __future__ import annotations

import pytest

from snowmcp.application.graph import GraphService
from snowmcp.application.local import UndoService
from snowmcp.application.ports import Response
from snowmcp.application.records import RecordService, _as_int
from snowmcp.application.responses import error_detail, unwrap_list
from snowmcp.application.services import CatalogService, CodeService, OpsService
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestGraphEdges:
    """Edges of the graph traversal."""

    def test_traversal_stops_at_the_node_limit(self) -> None:
        gateway = FakeGateway(
            default=records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})
        )
        service = GraphService(gateway, policy())

        nodes = service.traverse("p1", depth=3, limit=1)

        assert len(nodes) == 1

    def test_traversal_stops_when_the_frontier_empties(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = GraphService(gateway, policy())

        assert service.traverse("p1", depth=3) == []

    def test_a_failed_field_probe_is_not_a_field(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": ok({"result": []}),
                "/api/now/table/sys_dictionary": Response(status=500, body={}),
            },
            default=records({"name": "MyScript"}),
        )
        service = GraphService(gateway, policy())

        assert service.impact("MyScript", kind="auto")["kind"] == "script"

    def test_table_config_reads_a_dict_metadata_result(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": ok({"result": {"name": "incident"}}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["metadata"] == {"name": "incident"}

    def test_table_config_tolerates_a_missing_metadata_result(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": ok({"result": []}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["metadata"] == {}


class TestRecordEdges:
    """Edges of the record service."""

    def test_a_batch_only_journals_its_write_operations(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        journal = RecordingJournal()
        service = RecordService(gateway, policy(), journal=journal)

        service.batch(
            [
                {"method": "GET", "table": "incident"},
                {"method": "POST", "table": "incident", "body": {"short_description": "x"}},
            ],
            confirmed=True,
        )

        assert [entry.operation for entry in journal.entries] == ["post"]

    def test_a_batch_journal_entry_carries_the_body(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        journal = RecordingJournal()
        service = RecordService(gateway, policy(), journal=journal)

        service.batch(
            [{"method": "PATCH", "table": "incident", "body": {"sys_id": "abc", "state": "3"}}],
            confirmed=True,
        )

        assert journal.entries[0].sys_id == "abc"
        assert journal.entries[0].after == {"sys_id": "abc", "state": "3"}

    def test_a_batch_journal_entry_tolerates_a_non_dict_body(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        journal = RecordingJournal()
        service = RecordService(gateway, policy(), journal=journal)

        service.batch(
            [{"method": "POST", "table": "incident", "body": ["not", "a", "dict"]}],
            confirmed=True,
        )

        assert journal.entries[0].sys_id == ""

    def test_a_snapshot_that_raises_does_not_block_the_write(self) -> None:
        def responder(method, path, **kwargs):
            if method == "GET":
                raise RuntimeError("network down")
            return Response(status=200, body={"result": {"sys_id": "abc"}})

        gateway = FakeGateway()
        gateway.request = responder  # type: ignore[method-assign]
        service = RecordService(gateway, policy())

        assert service.update("incident", "abc", {"state": "3"}, confirmed=True).sys_id == "abc"

    def test_a_count_that_is_not_a_number_is_tolerated(self) -> None:
        gateway = FakeGateway(default=ok({"result": [], "total": "many"}))
        service = RecordService(gateway, policy())

        assert service.count("incident") == 0

    def test_a_count_of_none_is_tolerated(self) -> None:
        assert _as_int(None) is None

    def test_a_count_of_a_string_number_is_coerced(self) -> None:
        assert _as_int("42") == 42


class TestResponseEdges:
    """Edges of the response handling."""

    def test_an_error_detail_prefers_the_nested_message(self) -> None:
        assert error_detail({"error": {"message": "nested"}}) == "nested"

    def test_an_error_detail_falls_back_to_the_nested_detail(self) -> None:
        assert error_detail({"error": {"detail": "nested detail"}}) == "nested detail"

    def test_an_error_detail_ignores_a_non_string_message(self) -> None:
        assert error_detail({"error": {"message": 42}}) is None

    def test_an_error_detail_reads_the_detail_key(self) -> None:
        assert error_detail({"detail": "top detail"}) == "top detail"

    def test_an_error_detail_ignores_a_blank_string_body(self) -> None:
        assert error_detail("   ") is None

    def test_a_list_can_be_unwrapped_from_the_records_key(self) -> None:
        assert unwrap_list(Response(status=200, body={"records": [1, 2]})) == [1, 2]

    def test_a_list_can_be_unwrapped_from_the_results_key(self) -> None:
        assert unwrap_list(Response(status=200, body={"results": [3]})) == [3]


class TestServiceEdges:
    """Edges of the domain services."""

    def test_catalog_items_without_a_filter_send_no_query(self) -> None:
        gateway = FakeGateway(default=records({"name": "Laptop"}))
        service = CatalogService(gateway, policy())

        service.items()

        assert "sysparm_query" not in gateway.last().params

    def test_catalog_items_combine_a_category_and_a_text_filter(self) -> None:
        gateway = FakeGateway(default=ok([{"name": "Laptop"}]))
        service = CatalogService(gateway, policy())

        service.items(category="hardware", text="Lap")

        assert gateway.last().params["sysparm_category"] == "hardware"
        assert gateway.last().params["sysparm_text"] == "Lap"

    def test_the_log_can_be_filtered_by_source_alone(self) -> None:
        gateway = FakeGateway(default=records({"message": "oops"}))
        service = OpsService(gateway, policy())

        service.log(source="Workflow")

        assert gateway.last().params["sysparm_query"] == "source=Workflow"

    def test_the_log_without_filters_sends_no_query(self) -> None:
        gateway = FakeGateway(default=records({"message": "oops"}))
        service = OpsService(gateway, policy())

        service.log()

        assert "sysparm_query" not in gateway.last().params

    def test_properties_skip_rows_that_are_not_objects(self) -> None:
        gateway = FakeGateway(default=ok({"result": ["not a dict", {"name": "a", "value": "b"}]}))
        service = OpsService(gateway, policy())

        rows = service.properties()

        assert len(rows) == 1

    def test_listing_an_artefact_without_a_script_type_sends_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "Policy"}))
        service = CodeService(gateway, policy())

        service.list("acl")

        assert "sysparm_query" not in gateway.last().params

    def test_the_undo_service_lists_the_journal(self) -> None:
        service = UndoService(RecordingJournal(), FakeGateway())

        assert service.list() == []


class RecordingJournal:
    """A journal that keeps what it was told."""

    def __init__(self) -> None:
        self.entries = []

    def journal_append(self, entry):
        self.entries.append(entry)
        return entry

    def journal_list(self, limit=50):
        return []

    def journal_mark_reverted(self, entry_id):
        return True
