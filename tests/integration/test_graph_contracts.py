"""Tier 2 - the exact requests the graph service makes.

``GraphService`` carries its own probes for tables, fields and scripts. A
probe that asks the wrong question still returns a plausible answer, so
these tests pin the request itself - path, method and every query
parameter - rather than what comes back.
"""

from __future__ import annotations

from snowmcp.application.graph import GraphService
from snowmcp.application.ports import Response
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestGraphProbeContract:
    """The exact requests the probes make."""

    def test_a_table_probe_asks_sys_db_object_by_exact_name(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = GraphService(gateway, policy())

        service.table_config("incident")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_db_object"
        assert call.params == {"sysparm_query": "name=incident", "sysparm_limit": "1"}

    def test_a_field_listing_asks_sys_dictionary_for_that_table(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        service.table_config("incident")

        # `table_config` reads the dictionary first and the object second.
        call = gateway.calls[0]
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params == {"sysparm_query": "name=incident", "sysparm_limit": "500"}

    def test_a_field_reference_listing_asks_for_both_reference_forms(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        service.field_references("short_description")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params["sysparm_query"] == (
            "element_reference_name=short_description^ORname=short_description"
        )
        assert call.params["sysparm_limit"] == "200"

    def test_a_script_reference_listing_asks_sys_script(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = GraphService(gateway, policy())

        service.script_references("incident")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_script"
        assert call.params["sysparm_query"] == (
            "scriptLIKEincident^ORnameLIKEincident^ORdescriptionLIKEincident"
        )
        assert call.params["sysparm_limit"] == "100"


class TestGraphProbeFailures:
    """A failed probe short-circuits, it does not read the body.

    The error path has to be distinguishable from the success path: a
    failed response that nonetheless carries a result must still be
    reported as a failure. Without this, the guard can be inverted and
    nothing notices.
    """

    def test_a_failed_table_probe_reports_no_table_even_with_a_result(self) -> None:
        gateway = FakeGateway(
            default=Response(status=500, body={"result": [{"name": "incident"}]})
        )
        service = GraphService(gateway, policy())

        assert service._is_table("incident") is False

    def test_a_failed_field_probe_reports_no_field_even_with_a_result(self) -> None:
        gateway = FakeGateway(
            default=Response(status=500, body={"result": [{"element_id": "x"}]})
        )
        service = GraphService(gateway, policy())

        assert service._is_field("short_description") is False

    def test_a_failed_table_probe_does_not_fall_through_to_the_body(self) -> None:
        gateway = FakeGateway(
            default=Response(status=500, body={"result": [{"name": "incident"}]})
        )
        service = GraphService(gateway, policy())

        service._is_table("incident")

        assert gateway.last().path == "/api/now/table/sys_db_object"

    def test_a_successful_table_probe_reports_a_table(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = GraphService(gateway, policy())

        assert service._is_table("incident") is True

    def test_a_successful_field_probe_reports_a_field(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        assert service._is_field("short_description") is True


class TestRelationTypeResolution:
    """Relationship type labels are resolved once per distinct type."""

    def test_one_type_shared_by_many_relations_is_looked_up_once(self) -> None:
        many = [
            {"parent": "p1", "child": f"c{index}", "type": "type1"}
            for index in range(50)
        ]
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(*many),
                "/api/now/table/cmdb_rel_type": records({"name": "Contains"}),
            }
        )
        service = GraphService(gateway, policy())

        relations = service.relations("p1")

        lookups = [call for call in gateway.calls if call.path == "/api/now/table/cmdb_rel_type"]
        assert len(lookups) == 1
        assert lookups[0].params == {
            "sysparm_query": "sys_id=type1",
            "sysparm_limit": "1",
        }
        assert all(relation.type_label == "Contains" for relation in relations)

    def test_two_distinct_types_are_looked_up_once_each(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records(
                    {"parent": "p1", "child": "c1", "type": "type1"},
                    {"parent": "p1", "child": "c2", "type": "type2"},
                    {"parent": "p1", "child": "c3", "type": "type1"},
                ),
                "/api/now/table/cmdb_rel_type": records({"name": "Contains"}),
            }
        )
        service = GraphService(gateway, policy())

        service.relations("p1")

        lookups = [call for call in gateway.calls if call.path == "/api/now/table/cmdb_rel_type"]
        assert len(lookups) == 2

    def test_a_relation_with_no_type_is_not_looked_up(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/cmdb_rel_ci": records({"parent": "p1", "child": "c1", "type": ""}),
            }
        )
        service = GraphService(gateway, policy())

        relations = service.relations("p1")

        lookups = [call for call in gateway.calls if call.path == "/api/now/table/cmdb_rel_type"]
        assert lookups == []
        assert relations[0].type_label == ""

    def test_resolving_an_empty_type_asks_the_instance_nothing(self) -> None:
        gateway = FakeGateway()
        service = GraphService(gateway, policy())

        assert service._relation_type_label("") == ""
        assert gateway.calls == []

    def test_a_type_that_is_not_found_resolves_to_an_empty_label(self) -> None:
        gateway = FakeGateway(
            responses={"/api/now/table/cmdb_rel_type": ok({"result": []})}
        )
        service = GraphService(gateway, policy())

        assert service._relation_type_label("type1") == ""


class TestGraphKindContract:
    """Which impact lens fits, decided by asking the instance."""

    def test_a_field_probe_asks_sys_dictionary_by_element_reference_name(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        service._is_field("short_description")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params == {
            "sysparm_query": "element_reference_name=short_description",
            "sysparm_limit": "1",
        }

    def test_a_table_probe_asks_sys_db_object_by_name(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = GraphService(gateway, policy())

        service._is_table("incident")

        call = gateway.last()
        assert call.method == "GET"
        assert call.path == "/api/now/table/sys_db_object"
        assert call.params == {"sysparm_query": "name=incident", "sysparm_limit": "1"}

    def test_a_name_that_is_a_table_is_reported_as_a_table(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": records({"name": "incident"}),
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service._guess_kind("incident") == "table"

    def test_a_name_that_is_only_a_field_is_reported_as_a_field(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": ok({"result": []}),
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service._guess_kind("short_description") == "field"

    def test_a_name_that_is_neither_is_reported_as_a_script(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": ok({"result": []}),
                "/api/now/table/sys_dictionary": ok({"result": []}),
            }
        )
        service = GraphService(gateway, policy())

        assert service._guess_kind("something") == "script"


class TestGraphTableConfig:
    """``table_config`` assembles two responses into one answer."""

    def test_the_metadata_is_the_first_row_of_a_list_result(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": records(
                    {"name": "incident"}, {"name": "incident_copy"}
                ),
            }
        )
        service = GraphService(gateway, policy())

        result = service.table_config("incident")

        assert result["metadata"] == {"name": "incident"}
        assert result["name"] == "incident"
        assert result["fields"] == [{"element_id": "x"}]

    def test_the_metadata_is_the_dict_when_the_result_is_a_dict(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": ok({"result": {"name": "incident"}}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["metadata"] == {"name": "incident"}

    def test_the_metadata_is_empty_when_the_table_is_unknown(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": ok({"result": []}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["metadata"] == {}

    def test_a_missing_result_leaves_the_metadata_empty(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": records({"element_id": "x"}),
                "/api/now/table/sys_db_object": ok({}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["metadata"] == {}

    def test_a_non_dict_field_row_is_dropped(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": ok({"result": ["not-a-row", {"element_id": "x"}]}),
                "/api/now/table/sys_db_object": records({"name": "incident"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["fields"] == [{"element_id": "x"}]

    def test_a_non_list_field_result_is_empty(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_dictionary": ok({"result": {"element_id": "x"}}),
                "/api/now/table/sys_db_object": records({"name": "incident"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.table_config("incident")["fields"] == []

    def test_a_non_dict_reference_row_is_dropped(self) -> None:
        gateway = FakeGateway(
            default=ok({"result": ["not-a-row", {"element_id": "x"}]})
        )
        service = GraphService(gateway, policy())

        assert service.field_references("short_description") == [{"element_id": "x"}]

    def test_a_non_list_reference_result_is_empty(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"element_id": "x"}}))
        service = GraphService(gateway, policy())

        assert service.field_references("short_description") == []

    def test_a_non_dict_script_row_is_dropped(self) -> None:
        gateway = FakeGateway(default=ok({"result": ["not-a-row", {"name": "x"}]}))
        service = GraphService(gateway, policy())

        assert service.script_references("incident") == [{"name": "x"}]

    def test_a_non_list_script_result_is_empty(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"name": "x"}}))
        service = GraphService(gateway, policy())

        assert service.script_references("incident") == []
