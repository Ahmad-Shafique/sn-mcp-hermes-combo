"""Tier 3 - QA tests. Every action of every tool, driven the way a client does.

The point of a consolidated surface is that one tool covers a whole domain.
That only holds if every action actually works, so this file walks the whole
matrix.
"""

from __future__ import annotations

import json

import pytest

from snowmcp.adapters.mcp.server import build_server

from tests.conftest import FakeGateway, ok, records


@pytest.fixture
def server(services):
    """The MCP server, wired to the fake instance."""
    return build_server(services)


async def call(server, tool: str, **arguments):
    """Call a tool and return its payload."""
    result = await server.call_tool(tool, arguments)
    return json.loads(result.content[0].text)


@pytest.mark.qa
async def test_sn_write_update(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"sys_id": "abc"}})

    result = await call(
        server, "sn_write", action="update", table="incident", sys_id="abc", fields={"state": "3"}, confirm=True
    )

    assert result["sys_id"] == "abc"
    assert gateway.last().method == "PATCH"


@pytest.mark.qa
async def test_sn_write_delete(server, gateway: FakeGateway) -> None:
    gateway.default = ok({})

    result = await call(
        server, "sn_write", action="delete", table="incident", sys_id="abc", confirm=True
    )

    assert result["deleted"] is True


@pytest.mark.qa
async def test_sn_aggregate_group(server, gateway: FakeGateway) -> None:
    gateway.default = ok([{"group": "2", "aggregate": 5}])

    result = await call(
        server, "sn_aggregate", action="group", table="incident", aggregate="COUNT", group_by="state"
    )

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_schema_tables(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "incident"})

    result = await call(server, "sn_schema", action="tables", pattern="inc")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_schema_class(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "Server"})

    result = await call(server, "sn_schema", action="class", name="Server")

    assert result["name"] == "Server"


@pytest.mark.qa
async def test_sn_schema_references(server, gateway: FakeGateway) -> None:
    gateway.default = records({"element_id": "x"})

    result = await call(server, "sn_schema", action="references", name="short_description")

    assert result["field"] == "short_description"
    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_graph_relations(server, gateway: FakeGateway) -> None:
    gateway.default = records({"parent": "p1", "child": "c1", "type": "t1"})

    result = await call(server, "sn_graph", action="relations", sys_id="p1")

    assert result["count"] == 1
    assert result["relations"][0]["parent_sys_id"] == "p1"


@pytest.mark.qa
async def test_sn_graph_dependents(server, gateway: FakeGateway) -> None:
    gateway.default = records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})

    result = await call(server, "sn_graph", action="dependents", sys_id="p1", depth=1)

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_graph_csdm_models(server, gateway: FakeGateway) -> None:
    gateway.responses["/api/now/table/sys_db_object"] = records({"name": "sys_csdm_domain_model"})
    gateway.default = records({"name": "Service Domain"})

    result = await call(server, "sn_graph", action="csdm")

    assert result["available"] is True
    assert result["models"][0]["name"] == "Service Domain"


@pytest.mark.qa
async def test_sn_graph_csdm_contexts(server, gateway: FakeGateway) -> None:
    gateway.responses["/api/now/table/sys_db_object"] = records({"name": "sys_csdm_context"})
    gateway.default = records({"name": "Service Domain"})

    result = await call(server, "sn_graph", action="csdm", model="Service Domain")

    assert result["model"] == "Service Domain"
    assert result["contexts"][0]["name"] == "Service Domain"


@pytest.mark.qa
async def test_sn_catalog_categories(server, gateway: FakeGateway) -> None:
    gateway.default = records({"title": "Services"})

    result = await call(server, "sn_catalog", action="categories")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_catalog_variables(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"name": "Laptop", "variables": [{"name": "size"}]})

    result = await call(server, "sn_catalog", action="variables", item="item1")

    assert result["variables"][0]["name"] == "size"


@pytest.mark.qa
async def test_sn_catalog_order(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"number": "REQ01"})

    result = await call(
        server, "sn_catalog", action="order", item="item1", variables={"size": "M"}, confirm=True
    )

    assert result["number"] == "REQ01"


@pytest.mark.qa
async def test_sn_files_upload(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"sys_id": "att1"})

    result = await call(
        server,
        "sn_files",
        action="upload",
        table="incident",
        sys_id="abc",
        name="a.txt",
        content_base64="Zm9v",
        confirm=True,
    )

    assert result["sys_id"] == "att1"


@pytest.mark.qa
async def test_sn_files_download(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"content": "Zm9v"})

    result = await call(server, "sn_files", action="download", sys_id="att1")

    assert result["content"] == "Zm9v"


@pytest.mark.qa
async def test_sn_files_delete(server, gateway: FakeGateway) -> None:
    gateway.default = ok({})

    result = await call(server, "sn_files", action="delete", sys_id="att1", confirm=True)

    assert result["deleted"] is True


@pytest.mark.qa
async def test_sn_code_list(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "Policy"})

    result = await call(server, "sn_code", action="list", artefact="ui_policy")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_code_read(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"script": "var x = 1;"}})

    result = await call(server, "sn_code", action="read", table="sys_script", sys_id="abc")

    assert result["script"] == "var x = 1;"


@pytest.mark.qa
async def test_sn_code_where_used(server, gateway: FakeGateway) -> None:
    gateway.default = records({"element_id": "x"})

    result = await call(server, "sn_code", action="where_used", name="short_description")

    assert result["name"] == "short_description"


@pytest.mark.qa
async def test_sn_ops_log(server, gateway: FakeGateway) -> None:
    gateway.default = records({"message": "oops"})

    result = await call(server, "sn_ops", action="log", level="error")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_ops_jobs(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "Nightly"})

    result = await call(server, "sn_ops", action="jobs")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_ops_properties(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "public", "value": "visible"})

    result = await call(server, "sn_ops", action="properties")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_ops_stats(server, gateway: FakeGateway) -> None:
    gateway.default = ok([{"aggregate": 3}])

    result = await call(server, "sn_ops", action="stats")

    assert result["counts"]["incident"] == [{"aggregate": 3}]


@pytest.mark.qa
async def test_sn_local_note_search(server) -> None:
    await call(server, "sn_local", action="note_write", key="a", title="Alpha", body="needle")
    await call(server, "sn_local", action="note_write", key="b", title="Beta", body="other")

    result = await call(server, "sn_local", action="note_search", body="needle")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_local_note_list(server) -> None:
    await call(server, "sn_local", action="note_write", key="a", title="Alpha", body="x")

    result = await call(server, "sn_local", action="note_list")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_local_note_delete(server) -> None:
    await call(server, "sn_local", action="note_write", key="a", title="Alpha", body="x")

    result = await call(server, "sn_local", action="note_delete", key="a")

    assert result["deleted"] is True


@pytest.mark.qa
async def test_sn_local_cache_list(server) -> None:
    await call(
        server, "sn_local", action="cache_put", table="incident", sys_id="abc", payload={"n": 1}
    )

    result = await call(server, "sn_local", action="cache_list", table="incident")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_local_cache_get_of_a_missing_record(server) -> None:
    result = await call(server, "sn_local", action="cache_get", table="incident", sys_id="nope")

    assert result["found"] is False


@pytest.mark.qa
async def test_sn_local_saved_list(server) -> None:
    await call(server, "sn_local", action="saved_save", name="open", table="incident")

    result = await call(server, "sn_local", action="saved_list")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_local_undo_reverts_a_journalled_write(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"sys_id": "new"}})
    await call(
        server, "sn_write", action="create", table="incident", fields={"short_description": "x"}, confirm=True
    )
    gateway.default = ok({})

    result = await call(
        server, "sn_local", action="undo", entry_id="create:incident:new", confirm=True
    )

    assert result["reverted"] is True
    assert gateway.last().method == "DELETE"


@pytest.mark.qa
async def test_sn_admin_set_update_set(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"sys_id": "us1"}})

    result = await call(
        server, "sn_admin", action="set_update_set", update_set="Sprint 1", confirm=True
    )

    assert result["update_set"] == "Sprint 1"


@pytest.mark.qa
async def test_sn_admin_script(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {}})

    with pytest.raises(Exception, match=r"needs SN_SCRIPTED_REST_URL"):
        await call(server, "sn_admin", action="script", script="var x = 1;", confirm=True)


@pytest.mark.qa
async def test_sn_admin_atf(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {}})

    await call(server, "sn_admin", action="atf", suite="Suite", confirm=True)

    assert gateway.last().path == "/api/now/now/atf/suite/Suite/run"


@pytest.mark.qa
async def test_sn_admin_users(server, gateway: FakeGateway) -> None:
    gateway.default = records({"user_name": "a"})

    result = await call(server, "sn_admin", action="users", text="a")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_admin_groups(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "Support"})

    result = await call(server, "sn_admin", action="groups")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_admin_roles(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "admin"})

    result = await call(server, "sn_admin", action="roles", text="admin")

    assert result["count"] == 1


@pytest.mark.qa
async def test_sn_admin_memberships(server, gateway: FakeGateway) -> None:
    gateway.default = records({"member": "u1"})

    result = await call(server, "sn_admin", action="memberships", group="Support")

    assert result["members"][0]["member"] == "u1"
