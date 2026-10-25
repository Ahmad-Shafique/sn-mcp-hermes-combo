"""Tier 3 - QA tests. The MCP surface itself, end to end.

These drive the real server object the way a client does: list the tools,
then call them. They are the tests that catch a wiring mistake no unit or
integration test can see.
"""

from __future__ import annotations

import json

import pytest

from snowmcp.adapters.mcp.server import build_server
from snowmcp.application.ports import Response

from tests.conftest import FakeGateway, ok, records

EXPECTED_TOOLS = {
    "sn_read",
    "sn_write",
    "sn_aggregate",
    "sn_schema",
    "sn_graph",
    "sn_catalog",
    "sn_files",
    "sn_code",
    "sn_ops",
    "sn_local",
    "sn_admin",
}

READ_ONLY_TOOLS = {"sn_read", "sn_aggregate", "sn_schema", "sn_graph", "sn_code", "sn_ops"}


@pytest.fixture
def server(services):
    """The MCP server, wired to the fake instance."""
    return build_server(services)


async def call(server, tool: str, **arguments):
    """Call a tool and return its payload."""
    result = await server.call_tool(tool, arguments)
    text = result.content[0].text
    return json.loads(text)


@pytest.mark.qa
async def test_the_server_exposes_a_small_consolidated_surface(server) -> None:
    tools = await server.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == 11


@pytest.mark.qa
async def test_read_only_tools_are_annotated_as_such(server) -> None:
    tools = await server.list_tools()

    by_name = {tool.name: tool for tool in tools}
    for name in READ_ONLY_TOOLS:
        assert by_name[name].annotations.read_only_hint is True, name
    for name in EXPECTED_TOOLS - READ_ONLY_TOOLS:
        assert by_name[name].annotations.read_only_hint is False, name


@pytest.mark.qa
async def test_the_write_tool_is_marked_destructive(server) -> None:
    tools = await server.list_tools()

    by_name = {tool.name: tool for tool in tools}
    assert by_name["sn_write"].annotations.destructive_hint is True


@pytest.mark.qa
async def test_every_tool_documents_its_actions(server) -> None:
    tools = await server.list_tools()

    for tool in tools:
        assert tool.description, tool.name
        assert "action" in tool.description or "action=" in tool.description, tool.name


@pytest.mark.qa
async def test_reading_records_returns_them(server, gateway: FakeGateway) -> None:
    gateway.default = records({"sys_id": "abc", "number": "INC01"})

    result = await call(server, "sn_read", action="query", table="incident")

    assert result["count"] == 1
    assert result["records"][0]["fields"]["number"] == "INC01"


@pytest.mark.qa
async def test_reading_one_record_returns_it(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"sys_id": "abc", "number": "INC01"}})

    result = await call(server, "sn_read", action="get", table="incident", sys_id="abc")

    assert result["sys_id"] == "abc"
    assert result["fields"]["number"] == "INC01"


@pytest.mark.qa
async def test_counting_records_answers_in_one_call(server, gateway: FakeGateway) -> None:
    gateway.default = Response(status=200, body={"result": [], "total": 12})

    result = await call(server, "sn_read", action="count", table="incident")

    assert result["count"] == 12
    assert len(gateway.calls) == 1


@pytest.mark.qa
async def test_a_write_without_confirmation_is_refused(server, gateway: FakeGateway) -> None:
    with pytest.raises(Exception, match=r"needs confirmation"):
        await call(server, "sn_write", action="create", table="incident", fields={"a": 1})

    assert gateway.calls == []


@pytest.mark.qa
async def test_a_confirmed_write_is_applied_and_journalled(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": {"sys_id": "new"}})

    result = await call(
        server, "sn_write", action="create", table="incident", fields={"short_description": "x"}, confirm=True
    )

    assert result["sys_id"] == "new"
    journal = await call(server, "sn_local", action="journal")
    assert journal["count"] == 1


@pytest.mark.qa
async def test_a_batch_writes_many_records_in_one_call(server, gateway: FakeGateway) -> None:
    gateway.default = ok({"result": [{"sys_id": "a"}, {"sys_id": "b"}]})

    result = await call(
        server,
        "sn_write",
        action="batch",
        operations=[
            {"method": "POST", "table": "incident", "body": {"short_description": "one"}},
            {"method": "POST", "table": "incident", "body": {"short_description": "two"}},
        ],
        confirm=True,
    )

    assert result["count"] == 2
    assert len(gateway.calls) == 1


@pytest.mark.qa
async def test_aggregates_answer_how_many_in_one_call(server, gateway: FakeGateway) -> None:
    gateway.default = ok([{"group": "2", "aggregate": 5}])

    result = await call(server, "sn_aggregate", action="stats", table="incident", aggregate="COUNT")

    assert result["rows"][0]["aggregate"] == 5


@pytest.mark.qa
async def test_the_graph_traversal_reports_the_nodes_it_reached(server, gateway: FakeGateway) -> None:
    gateway.default = records({"parent": "p1", "child": "c1", "type": "t1", "child_type": "app"})

    result = await call(server, "sn_graph", action="traverse", sys_id="p1", depth=1)

    assert result["count"] == 1
    assert result["nodes"][0]["sys_id"] == "c1"


@pytest.mark.qa
async def test_impact_analysis_reports_the_references(server, gateway: FakeGateway) -> None:
    gateway.default = records({"element_id": "x"})

    result = await call(server, "sn_graph", action="impact", target="short_description", kind="field")

    assert result["kind"] == "field"
    assert result["field_references"][0]["element_id"] == "x"


@pytest.mark.qa
async def test_a_note_is_stored_and_read_back(server) -> None:
    await call(server, "sn_local", action="note_write", key="runbook", title="Runbook", body="steps")

    result = await call(server, "sn_local", action="note_read", key="runbook")

    assert result["body"] == "steps"


@pytest.mark.qa
async def test_a_saved_query_runs_in_one_later_call(server, gateway: FakeGateway) -> None:
    await call(
        server, "sn_local", action="saved_save", name="open", table="incident", encoded_query="state=2"
    )
    gateway.default = records({"sys_id": "a"})

    result = await call(server, "sn_local", action="saved_run", name="open")

    assert result["count"] == 1
    assert result["name"] == "open"


@pytest.mark.qa
async def test_a_cached_record_avoids_a_second_api_call(server, gateway: FakeGateway) -> None:
    await call(
        server,
        "sn_local",
        action="cache_put",
        table="incident",
        sys_id="abc",
        payload={"number": "INC01"},
    )

    result = await call(server, "sn_local", action="cache_get", table="incident", sys_id="abc")

    assert result["payload"]["number"] == "INC01"
    assert gateway.calls == []


@pytest.mark.qa
async def test_the_call_history_records_what_was_done(server, gateway: FakeGateway) -> None:
    gateway.default = records({"sys_id": "abc"})

    await call(server, "sn_read", action="query", table="incident")
    result = await call(server, "sn_local", action="history")

    assert result["count"] == 1
    assert "incident" in result["calls"][0]["summary"]


@pytest.mark.qa
async def test_undo_needs_confirmation(server) -> None:
    with pytest.raises(Exception, match=r"undo requires confirmation"):
        await call(server, "sn_local", action="undo", entry_id="create:incident:abc")


@pytest.mark.qa
async def test_the_catalog_lists_items(server, gateway: FakeGateway) -> None:
    gateway.default = ok([{"name": "Laptop"}])

    result = await call(server, "sn_catalog", action="items", text="Laptop")

    assert result["count"] == 1


@pytest.mark.qa
async def test_the_ops_health_check_reports_the_version(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "glide.sys.version", "value": "Tokyo"})

    result = await call(server, "sn_ops", action="health")

    assert result["version"] == "Tokyo"


@pytest.mark.qa
async def test_code_search_finds_scripts(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "MyScript"})

    result = await call(server, "sn_code", action="search", text="MyScript")

    assert result["count"] == 1


@pytest.mark.qa
async def test_schema_reads_a_tables_fields(server, gateway: FakeGateway) -> None:
    gateway.default = records({"element_id": "x"})

    result = await call(server, "sn_schema", action="fields", table="incident")

    assert result["table"] == "incident"
    assert result["count"] == 1


@pytest.mark.qa
async def test_the_admin_surface_lists_update_sets(server, gateway: FakeGateway) -> None:
    gateway.default = records({"name": "Sprint 1"})

    result = await call(server, "sn_admin", action="update_sets")

    assert result["count"] == 1


@pytest.mark.qa
async def test_files_list_the_attachments_on_a_record(server, gateway: FakeGateway) -> None:
    gateway.default = records({"file_name": "a.png"})

    result = await call(server, "sn_files", action="list", table="incident", sys_id="abc")

    assert result["count"] == 1
