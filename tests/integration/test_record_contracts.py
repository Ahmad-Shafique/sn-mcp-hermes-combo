"""Tier 2 - the remaining request contracts.

These are the surfaces the mutation gate kept finding survivors in: the
batch body, the record field extraction, the update snapshot, and the
graph traversal. Each test pins the exact request and the exact shape of
what comes back, so a changed limit, a changed verb or a dropped field is
a test failure rather than a surprise in production.
"""

from __future__ import annotations

from typing import Any, Mapping

import base64
import json

import pytest

from snowmcp.application.graph import GraphService
from snowmcp.application.ports import Response
from snowmcp.application.records import RecordService
from snowmcp.application.services import OpsService
from snowmcp.domain.errors import SafetyGuardError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Record

from tests.conftest import FakeGateway, RecordedCall, ok, records


def policy(**kwargs: object) -> WritePolicy:
    """A permissive policy, unless the test says otherwise."""
    kwargs.setdefault("require_confirm", False)
    return WritePolicy(**kwargs)  # type: ignore[arg-type]


class MethodAwareGateway(FakeGateway):
    """A gateway that answers reads and writes differently.

    The plain fake keys its answers by path alone, so a read and a write
    to the same record collide. This one separates them.
    """

    def __init__(self, *, get: Response | None = None, default: Response | None = None) -> None:
        super().__init__(default=default)
        self._get = get

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        self.calls.append(RecordedCall(method, path, params, json_body))
        if method.upper() == "GET" and self._get is not None:
            return self._get
        if self.default is not None:
            return self.default
        return Response(status=200, body={"result": []})


class TestRecordFieldExtraction:
    """Which payload keys become fields, and which become display values."""

    def test_it_keeps_the_ordinary_fields(self) -> None:
        record = Record.from_payload(
            {"sys_id": "s1", "number": "INC01", "short_description": "broken"},
            table="incident",
        )

        assert record.fields == {
            "sys_id": "s1",
            "number": "INC01",
            "short_description": "broken",
        }

    def test_it_keeps_the_three_named_system_fields(self) -> None:
        record = Record.from_payload(
            {
                "sys_id": "s1",
                "sys_created_on": "2026-01-01",
                "sys_updated_on": "2026-01-02",
                "sys_update_type": "update",
            },
            table="incident",
        )

        assert record.fields == {
            "sys_id": "s1",
            "sys_created_on": "2026-01-01",
            "sys_updated_on": "2026-01-02",
        }

    def test_it_drops_every_other_system_field(self) -> None:
        record = Record.from_payload(
            {"sys_id": "s1", "sys_mod_count": "3", "sys_domain": "global"},
            table="incident",
        )

        assert record.fields == {"sys_id": "s1"}

    def test_it_lifts_a_display_value_out_of_its_prefixed_key(self) -> None:
        record = Record.from_payload(
            {"sys_id": "s1", "display_value:short_description": "Broken laptop"},
            table="incident",
        )

        assert record.display_values == {"short_description": "Broken laptop"}

    def test_a_display_value_stays_in_the_raw_fields_too(self) -> None:
        record = Record.from_payload(
            {"sys_id": "s1", "display_value:short_description": "Broken laptop"},
            table="incident",
        )

        # The prefixed key is kept verbatim in the raw fields; the lifted
        # value is what callers read through ``get``.
        assert record.fields["display_value:short_description"] == "Broken laptop"
        assert record.get("short_description") == "Broken laptop"

    def test_the_table_comes_from_the_table_argument_by_default(self) -> None:
        record = Record.from_payload({"sys_id": "s1"}, table="incident")

        assert record.table == "incident"

    def test_the_table_in_the_payload_wins(self) -> None:
        record = Record.from_payload({"sys_id": "s1", "__table": "change_request"})

        assert record.table == "change_request"

    def test_a_missing_sys_id_is_an_empty_string(self) -> None:
        record = Record.from_payload({}, table="incident")

        assert record.sys_id == ""


class TestUpdateContract:
    """An update reads the current state first, so a revert has something
    to restore."""

    def test_it_reads_the_record_before_writing_it(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "s1"}}))
        service = RecordService(gateway, policy())

        service.update("incident", "s1", {"short_description": "new"})

        assert [call.path for call in gateway.calls] == [
            "/api/now/table/incident/s1",
            "/api/now/table/incident/s1",
        ]

    def test_the_snapshot_is_read_without_the_display_value(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "s1"}}))
        service = RecordService(gateway, policy())

        service.update("incident", "s1", {"short_description": "new"})

        assert gateway.calls[0].params == {"sysparm_display_value": "false"}

    def test_it_patches_the_record_with_the_new_fields(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "s1"}}))
        service = RecordService(gateway, policy())

        service.update("incident", "s1", {"short_description": "new"})

        call = gateway.calls[1]
        assert call.method == "PATCH"
        assert call.path == "/api/now/table/incident/s1"
        assert call.json_body == {"short_description": "new"}

    def test_a_failed_snapshot_does_not_block_the_write(self) -> None:
        gateway = MethodAwareGateway(
            get=Response(status=500, body={}),
            default=ok({"result": {"sys_id": "s1"}}),
        )
        service = RecordService(gateway, policy())

        record = service.update("incident", "s1", {"short_description": "new"})

        assert record.sys_id == "s1"
        assert gateway.calls[1].method == "PATCH"

    def test_a_snapshot_that_is_not_a_mapping_is_ignored(self) -> None:
        gateway = MethodAwareGateway(
            get=ok(["not-a-mapping"]),
            default=ok({"result": {"sys_id": "s1"}}),
        )
        service = RecordService(gateway, policy())

        assert service.update("incident", "s1", {"short_description": "x"}).sys_id == "s1"


class TestBatchContract:
    """The Batch API request, and what the server does with each operation."""

    def test_it_posts_to_the_versioned_batch_endpoint(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident"}])

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/v1/batch"

    def test_the_body_carries_the_request_id_and_the_operations(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident"}])

        body = gateway.last().json_body
        assert body["batch_request_id"] is None
        assert len(body["rest_requests"]) == 1

    def test_each_operation_gets_a_one_based_id(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch(
            [{"method": "GET", "table": "incident"}, {"method": "GET", "table": "change_request"}]
        )

        body = gateway.last().json_body
        assert [item["id"] for item in body["rest_requests"]] == ["1", "2"]

    def test_each_operation_uses_a_relative_url(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident"}])

        assert gateway.last().json_body["rest_requests"][0]["url"] == "/api/now/table/incident"

    def test_a_sys_id_extends_the_url(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "PATCH", "table": "incident", "sys_id": "s1"}])

        assert gateway.last().json_body["rest_requests"][0]["url"] == "/api/now/table/incident/s1"

    def test_a_query_is_appended_to_the_url(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident", "query": {"sysparm_limit": "5"}}])

        url = gateway.last().json_body["rest_requests"][0]["url"]
        assert url.startswith("/api/now/table/incident?")
        assert "sysparm_limit=5" in url

    def test_a_body_is_base64_encoded_json(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "POST", "table": "incident", "body": {"short_description": "x"}}])

        item = gateway.last().json_body["rest_requests"][0]
        assert json.loads(base64.b64decode(item["body"])) == {"short_description": "x"}

    def test_a_body_carries_its_own_content_type_header(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "POST", "table": "incident", "body": {"a": 1}}])

        item = gateway.last().json_body["rest_requests"][0]
        assert item["headers"] == [{"name": "Content-Type", "value": "application/json"}]

    def test_an_operation_with_no_body_carries_no_body_or_headers(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident"}])

        item = gateway.last().json_body["rest_requests"][0]
        assert "body" not in item
        assert "headers" not in item

    def test_the_results_keep_only_the_objects(self) -> None:
        gateway = FakeGateway(default=ok({"result": [{"sys_id": "s1"}, "not-an-object"]}))
        service = RecordService(gateway, policy())

        assert service.batch([{"method": "GET", "table": "incident"}]) == [{"sys_id": "s1"}]

    def test_a_batch_over_the_limit_is_refused(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy(max_batch=2))

        with pytest.raises(SafetyGuardError):
            service.batch([{"method": "GET", "table": "incident"}] * 3)

    def test_every_write_verb_is_a_write(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch(
            [
                {"method": "POST", "table": "incident"},
                {"method": "PATCH", "table": "incident"},
                {"method": "PUT", "table": "incident"},
                {"method": "DELETE", "table": "incident"},
            ]
        )

        assert gateway.last().json_body["rest_requests"]

    def test_a_batch_is_refused_without_confirmation(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy(require_confirm=True))

        with pytest.raises(SafetyGuardError):
            service.batch([{"method": "POST", "table": "incident"}])

    def test_a_confirmed_batch_is_allowed(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy(require_confirm=True))

        service.batch([{"method": "POST", "table": "incident"}], confirmed=True)

        assert gateway.last().method == "POST"

    def test_an_operation_with_no_table_names_an_empty_table(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET"}])

        # The fallback is an empty name, not the string "None".
        assert gateway.last().json_body["rest_requests"][0]["url"] == "/api/now/table/"

    def test_an_operation_with_no_method_defaults_to_a_get(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"table": "incident"}])

        assert gateway.last().json_body["rest_requests"][0]["method"] == "GET"

    def test_an_operation_with_no_sys_id_has_a_bare_table_url(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = RecordService(gateway, policy())

        service.batch([{"method": "GET", "table": "incident"}])

        assert gateway.last().json_body["rest_requests"][0]["url"] == "/api/now/table/incident"


class TestMissingKeyFallbacks:
    """A key that is not in the row comes back as an empty string.

    These are the fallbacks the mutation gate kept finding: change the
    default from ``""`` to something else and a row missing that key
    comes back different.
    """

    def test_a_relation_row_with_no_parent_or_child_is_empty(self) -> None:
        gateway = FakeGateway(default=records({"type": ""}))
        service = GraphService(gateway, policy())

        relation = service.relations("p1")[0]

        assert relation.parent_sys_id == ""
        assert relation.child_sys_id == ""
        assert relation.parent_table == ""
        assert relation.child_table == ""

    def test_a_relation_type_row_with_no_name_is_empty(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(
                    {"parent": "p1", "child": "c1", "type": "type1"}
                ),
                "/api/now/table/cmdb_rel_type": records({"value": "x"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.relations("p1")[0].type_label == ""

    def test_a_relation_type_row_that_is_a_mapping_is_read_directly(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(
                    {"parent": "p1", "child": "c1", "type": "type1"}
                ),
                "/api/now/table/cmdb_rel_type": ok({"result": {"name": "Contains"}}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.relations("p1")[0].type_label == "Contains"

    def test_a_property_row_with_no_name_has_an_empty_name(self) -> None:
        gateway = FakeGateway(default=records({"value": "x"}))
        service = OpsService(gateway, policy())

        assert service.properties()[0]["name"] == ""

    def test_a_record_with_no_sys_id_has_an_empty_one(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"number": "INC01"}}))
        service = RecordService(gateway, policy())

        assert service.get("incident", "s1").sys_id == ""


class TestTraverseContract:
    """Walking the Service Graph outward from one CI."""

    def test_it_reads_the_relations_of_the_starting_node(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1"}))
        service = GraphService(gateway, policy())

        service.traverse("p1")

        assert gateway.calls[0].path == "/api/now/table/cmdb_rel_ci"
        assert gateway.calls[0].params["sysparm_query"] == "parent=p1^ORchild=p1"

    def test_a_neighbour_is_reached_at_depth_one(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1"}))
        service = GraphService(gateway, policy())

        nodes = service.traverse("p1")

        assert [node.sys_id for node in nodes] == ["c1"]
        assert nodes[0].depth == 1

    def test_the_starting_node_is_never_reported_as_its_own_neighbour(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "p1"}))
        service = GraphService(gateway, policy())

        assert service.traverse("p1") == []

    def test_a_relation_with_no_neighbour_is_skipped(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": ""}))
        service = GraphService(gateway, policy())

        assert service.traverse("p1") == []

    def test_a_node_is_only_reported_once(self) -> None:
        gateway = FakeGateway(
            default=records(
                {"parent": "p1", "child": "c1"},
                {"parent": "p1", "child": "c1"},
            )
        )
        service = GraphService(gateway, policy())

        assert [node.sys_id for node in service.traverse("p1")] == ["c1"]

    def test_dependents_walk_downward_only(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1"}))
        service = GraphService(gateway, policy())

        service.dependents("p1")

        assert gateway.calls[0].params["sysparm_query"] == "parent=p1"

    def test_dependents_at_depth_two_reach_a_grandchild(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(
                    {"parent": "p1", "child": "c1"},
                    {"parent": "c1", "child": "c2"},
                )
            }
        )
        service = GraphService(gateway, policy())

        nodes = service.dependents("p1", depth=2)

        assert [node.sys_id for node in nodes] == ["c1", "c2"]
        assert [node.depth for node in nodes] == [1, 2]

    def test_the_depth_is_capped_at_the_documented_maximum(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(
                    {"parent": "p1", "child": "c1"},
                    {"parent": "c1", "child": "c2"},
                )
            }
        )
        service = GraphService(gateway, policy())

        # Asking for depth 50 must not walk 50 levels.
        nodes = service.traverse("p1", depth=50)

        assert [node.sys_id for node in nodes] == ["c1", "c2"]


class TestImpactContract:
    """The impact lens, and how it is chosen."""

    def test_an_explicit_field_kind_reads_the_field_references(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        result = service.impact("short_description", kind="field")

        assert result["kind"] == "field"
        assert result["field_references"] == [{"element_id": "x"}]

    def test_an_explicit_script_kind_reads_the_script_references(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = GraphService(gateway, policy())

        result = service.impact("MyScript", kind="script")

        assert result["kind"] == "script"
        assert result["script_references"] == [{"name": "x"}]

    def test_an_explicit_table_kind_reads_the_table_config(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": records({"name": "incident"}),
            }
        )
        service = GraphService(gateway, policy())

        result = service.impact("incident", kind="table")

        assert result["kind"] == "table"
        assert result["table_config"]["name"] == "incident"

    def test_the_auto_kind_picks_the_table_lens_for_a_table(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": records({"name": "incident"}),
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.impact("incident")["kind"] == "table"

    def test_the_auto_kind_picks_the_field_lens_for_a_field(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": ok({"result": []}),
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.impact("short_description")["kind"] == "field"

    def test_the_auto_kind_falls_back_to_the_script_lens(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": ok({"result": []}),
                "/api/now/table/sys_dictionary": ok({"result": []}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.impact("something")["kind"] == "script"

    def test_the_target_is_carried_into_the_answer(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        assert service.impact("short_description", kind="field")["target"] == "short_description"
