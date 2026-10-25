"""Tier 2 - contract tests: exactly what this server asks the instance for.

The other tiers assert behaviour - what comes back. These assert the *request*:
the exact path, the exact query parameters, the exact body. A service that
quietly changes the limit it sends, drops a filter, or posts to the wrong
endpoint still "works" against a fake that answers everything, and only fails
in production.

That is exactly the class of bug mutation testing keeps finding here.
"""

from __future__ import annotations

import pytest

from snowmcp.application.ports import Response
from snowmcp.application.records import AggregateService, RecordService, SchemaService
from snowmcp.application.local import SavedQueryService
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Query

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestRecordContract:
    """The exact requests the record service makes."""

    def test_query_sends_the_documented_table_api_parameters(self) -> None:
        gateway = FakeGateway(default=records({"sys_id": "a"}))
        service = RecordService(gateway, policy())

        service.query(
            Query(
                table="incident",
                encoded_query="state=2",
                fields=("number",),
                limit=25,
                offset=50,
                order_by="number",
                display_value=True,
            )
        )

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/incident"
        assert call.params == {
            "sysparm_limit": "25",
            "sysparm_query": "state=2",
            "sysparm_fields": "number",
            "sysparm_offset": "50",
            "sysparm_order_by": "number",
            "sysparm_display_value": "true",
        }

    def test_query_sends_only_the_limit_when_nothing_else_is_set(self) -> None:
        gateway = FakeGateway(default=records({"sys_id": "a"}))
        service = RecordService(gateway, policy())

        service.query(Query(table="incident"))

        assert gateway.last().params == {"sysparm_limit": "100"}

    def test_count_asks_for_one_row_but_reads_the_total(self) -> None:
        gateway = FakeGateway(default=Response(status=200, body={"result": [], "total": 9}))
        service = RecordService(gateway, policy())

        service.count("incident", "state=2")

        assert gateway.last().params == {"sysparm_query": "state=2", "sysparm_limit": "1"}

    def test_get_asks_for_the_display_value_of_one_record(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "abc"}}))
        service = RecordService(gateway, policy())

        service.get("incident", "abc")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/incident/abc"
        assert call.params == {"sysparm_display_value": "true"}

    def test_create_posts_to_the_table_collection(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "new"}}))
        service = RecordService(gateway, policy())

        service.create("incident", {"short_description": "x"}, confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/table/incident"
        assert call.json_body == {"short_description": "x"}
        assert call.params is None

    def test_update_patches_one_record_with_the_display_value_off(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "abc"}}))
        service = RecordService(gateway, policy())

        service.update("incident", "abc", {"state": "3"}, confirmed=True)

        call = gateway.last()
        assert call.method == "PATCH"
        assert call.path == "/api/now/table/incident/abc"
        assert call.json_body == {"state": "3"}

    def test_delete_deletes_one_record(self) -> None:
        gateway = FakeGateway(default=ok({}))
        service = RecordService(gateway, policy())

        service.delete("incident", "abc", confirmed=True)

        call = gateway.last()
        assert call.method == "DELETE"
        assert call.path == "/api/now/table/incident/abc"

    def test_the_snapshot_is_read_without_the_display_value(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "abc"}}))
        service = RecordService(gateway, policy())

        service.update("incident", "abc", {"state": "3"}, confirmed=True)

        snapshot = gateway.calls[0]
        assert snapshot.method == "GET"
        assert snapshot.params == {"sysparm_display_value": "false"}

    def test_batch_posts_to_the_versioned_batch_endpoint(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "POST", "table": "incident", "body": {"a": 1}}], confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/v1/batch"
        assert call.json_body["rest_requests"][0]["url"] == "/api/now/table/incident"
        assert call.json_body["rest_requests"][0]["method"] == "POST"
        assert call.json_body["rest_requests"][0]["id"] == "1"


class TestSchemaContract:
    """The exact requests the schema service makes."""

    def test_tables_asks_sys_db_object_for_a_pattern(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = SchemaService(gateway, policy())

        service.tables("inc", limit=30)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_db_object"
        assert call.params == {"sysparm_limit": "30", "sysparm_query": "nameLIKEinc"}

    def test_fields_asks_sys_dictionary_for_one_table(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = SchemaService(gateway, policy())

        service.fields("incident", limit=40)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params == {"sysparm_query": "name=incident", "sysparm_limit": "40"}

    def test_field_references_asks_for_both_reference_forms(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = SchemaService(gateway, policy())

        service.field_references("short_description")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params["sysparm_query"] == (
            "element_reference_name=short_description^ORname=short_description"
        )
        assert call.params["sysparm_limit"] == "200"


class TestAggregateContract:
    """The exact request the aggregate service makes."""

    def test_stats_asks_the_stats_endpoint_with_the_documented_parameters(self) -> None:
        gateway = FakeGateway(default=ok([{"aggregate": 1}]))
        service = AggregateService(gateway, policy())

        service.stats("incident", "COUNT", encoded_query="state=2", group_by="state")

        call = gateway.last()
        assert call.path == "/api/now/stats/incident"
        assert call.params == {
            "sysparm_aggregate": "COUNT",
            "sysparm_query": "state=2",
            "sysparm_group_by": "state",
        }


class TestSavedQueryContract:
    """The exact request a saved query makes."""

    def test_a_saved_query_reruns_with_its_own_parameters(self) -> None:
        gateway = FakeGateway(default=records({"sys_id": "a"}))
        store = _Store()
        service = SavedQueryService(store, gateway)
        service.save("open", "incident", encoded_query="state=2", fields=("number",), limit=7)

        service.run("open")

        call = gateway.last()
        assert call.path == "/api/now/table/incident"
        assert call.params == {
            "sysparm_query": "state=2",
            "sysparm_limit": "7",
            "sysparm_fields": "number",
        }


class _Store:
    """A store that holds one saved query."""

    def __init__(self) -> None:
        self.queries: dict[str, object] = {}

    def save_query(self, query):
        self.queries[query.name] = query
        return query

    def get_query(self, name):
        return self.queries.get(name)

    def list_queries(self):
        return list(self.queries.values())
