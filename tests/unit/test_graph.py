"""Tier 1 - unit tests for the Service Graph use cases."""

from __future__ import annotations

from snowmcp.application.graph import GraphService
from snowmcp.application.ports import Response
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def build_service(gateway: FakeGateway) -> GraphService:
    """A graph service over the fake gateway."""
    return GraphService(gateway, WritePolicy(require_confirm=False))


def test_relations_reads_the_relationship_table() -> None:
    gateway = FakeGateway(
        default=records(
            {
                "parent": "p1",
                "child": "c1",
                "type": "t1",
                "parent_type": "server",
                "child_type": "application",
            }
        )
    )
    service = build_service(gateway)

    relations = service.relations("p1")

    assert gateway.calls[0].path == "/api/now/table/cmdb_rel_ci"
    assert relations[0].parent_sys_id == "p1"
    assert relations[0].child_table == "application"


def test_relations_resolve_the_relationship_type_label() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/cmdb_rel_type": records({"name": "Contains"}),
        },
        default=records({"parent": "p1", "child": "c1", "type": "t1"}),
    )
    service = build_service(gateway)

    relations = service.relations("p1")

    assert relations[0].type_label == "Contains"


def test_a_relationship_type_that_cannot_be_resolved_has_no_label() -> None:
    gateway = FakeGateway(
        responses={"/api/now/table/cmdb_rel_type": Response(status=403, body={})},
        default=records({"parent": "p1", "child": "c1", "type": "t1"}),
    )
    service = build_service(gateway)

    assert service.relations("p1")[0].type_label == ""


def test_a_relationship_type_returned_as_a_dict_is_resolved() -> None:
    gateway = FakeGateway(
        responses={"/api/now/table/cmdb_rel_type": ok({"result": {"name": "Depends on"}})},
        default=records({"parent": "p1", "child": "c1", "type": "t1"}),
    )
    service = build_service(gateway)

    assert service.relations("p1")[0].type_label == "Depends on"


def test_an_unresolvable_relationship_type_yields_an_empty_label() -> None:
    gateway = FakeGateway(
        responses={"/api/now/table/cmdb_rel_type": ok({"result": []})},
        default=records({"parent": "p1", "child": "c1", "type": "t1"}),
    )
    service = build_service(gateway)

    assert service.relations("p1")[0].type_label == ""


def test_a_relationship_without_a_type_is_not_resolved() -> None:
    gateway = FakeGateway(default=records({"parent": "p1", "child": "c1", "type": ""}))
    service = build_service(gateway)

    assert service.relations("p1")[0].type_label == ""


def test_relations_skips_malformed_rows() -> None:
    gateway = FakeGateway(default=ok({"result": ["not a dict"]}))
    service = build_service(gateway)

    assert service.relations("p1") == []


def test_traverse_walks_outward_and_records_depth() -> None:
    gateway = FakeGateway(
        default=records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})
    )
    service = build_service(gateway)

    nodes = service.traverse("p1", depth=1)

    assert [node.sys_id for node in nodes] == ["c1"]
    assert nodes[0].depth == 1


def test_traverse_stops_at_the_depth_limit() -> None:
    gateway = FakeGateway(
        default=records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})
    )
    service = build_service(gateway)

    nodes = service.traverse("p1", depth=99)

    assert len(nodes) == 1


def test_traverse_never_revisits_a_node() -> None:
    gateway = FakeGateway(
        default=records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})
    )
    service = build_service(gateway)

    nodes = service.traverse("p1", depth=3)

    assert len({node.sys_id for node in nodes}) == len(nodes)


def test_dependents_walks_downward_only() -> None:
    gateway = FakeGateway(
        default=records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})
    )
    service = build_service(gateway)

    nodes = service.dependents("p1", depth=2)

    assert nodes[0].sys_id == "c1"
    assert "parent=p1" in gateway.calls[0].params["sysparm_query"]


def test_impact_on_a_table_reports_its_config() -> None:
    gateway = FakeGateway(default=records({"element_id": "x", "name": "incident"}))
    service = build_service(gateway)

    result = service.impact("incident", kind="table")

    assert result["kind"] == "table"
    assert result["table_config"]["name"] == "incident"


def test_impact_on_a_field_reports_its_references() -> None:
    gateway = FakeGateway(default=records({"element_id": "x"}))
    service = build_service(gateway)

    result = service.impact("short_description", kind="field")

    assert result["kind"] == "field"
    assert result["field_references"][0]["element_id"] == "x"


def test_impact_on_a_script_reports_its_references() -> None:
    gateway = FakeGateway(default=records({"name": "MyScript"}))
    service = build_service(gateway)

    result = service.impact("MyScript", kind="script")

    assert result["kind"] == "script"


def test_impact_auto_detects_a_table() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": records({"name": "incident"}),
            "/api/now/table/sys_dictionary": records({"element_id": "x"}),
        },
        default=records({"element_id": "x"}),
    )
    service = build_service(gateway)

    result = service.impact("incident", kind="auto")

    assert result["kind"] == "table"


def test_impact_auto_detects_a_field() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": ok({"result": []}),
            "/api/now/table/sys_dictionary": records({"element_id": "x"}),
        },
        default=records({"element_id": "x"}),
    )
    service = build_service(gateway)

    result = service.impact("short_description", kind="auto")

    assert result["kind"] == "field"


def test_impact_auto_falls_back_to_a_script() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": ok({"result": []}),
            "/api/now/table/sys_dictionary": ok({"result": []}),
        },
        default=records({"name": "MyScript"}),
    )
    service = build_service(gateway)

    result = service.impact("MyScript", kind="auto")

    assert result["kind"] == "script"


def test_impact_auto_treats_a_failed_probe_as_not_a_table() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": Response(status=500, body={}),
            "/api/now/table/sys_dictionary": ok({"result": []}),
        },
        default=records({"name": "MyScript"}),
    )
    service = build_service(gateway)

    result = service.impact("MyScript", kind="auto")

    assert result["kind"] == "script"


def test_csdm_models_lists_the_domain_models() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": records({"name": "sys_csdm_domain_model"}),
            "/api/now/table/sys_csdm_domain_model": records({"name": "Service Domain"}),
        }
    )
    service = build_service(gateway)

    result = service.csdm_models()

    assert result["available"] is True
    assert result["models"][0]["name"] == "Service Domain"


def test_csdm_models_reports_honestly_when_the_table_is_absent() -> None:
    """sys_csdm_domain_model is not in ServiceNow's public contract."""
    gateway = FakeGateway(
        responses={"/api/now/table/sys_db_object": ok({"result": []})},
    )
    service = build_service(gateway)

    result = service.csdm_models()

    assert result["available"] is False
    assert result["models"] == []
    assert "not part of ServiceNow's public documented contract" in result["reason"]


def test_a_failed_table_probe_counts_as_absent() -> None:
    gateway = FakeGateway(
        responses={"/api/now/table/sys_db_object": Response(status=403, body={})},
    )
    service = build_service(gateway)

    assert service.csdm_models()["available"] is False


def test_csdm_context_lists_the_contexts_of_a_model() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_db_object": records({"name": "sys_csdm_context"}),
            "/api/now/table/sys_csdm_context": records({"name": "Service Domain"}),
        }
    )
    service = build_service(gateway)

    result = service.csdm_context("Service Domain")

    assert result["available"] is True
    assert result["contexts"][0]["name"] == "Service Domain"


def test_csdm_context_reports_honestly_when_the_table_is_absent() -> None:
    gateway = FakeGateway(
        responses={"/api/now/table/sys_db_object": ok({"result": []})},
    )
    service = build_service(gateway)

    result = service.csdm_context("Service Domain")

    assert result["available"] is False
    assert result["contexts"] == []


def test_table_config_includes_the_object_metadata() -> None:
    gateway = FakeGateway(
        responses={
            "/api/now/table/sys_dictionary": records({"element_id": "x"}),
            "/api/now/table/sys_db_object": records({"name": "incident", "label": "Incident"}),
        }
    )
    service = build_service(gateway)

    config = service.table_config("incident")

    assert config["metadata"]["label"] == "Incident"
    assert len(config["fields"]) == 1
