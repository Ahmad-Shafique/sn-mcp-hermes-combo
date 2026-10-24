"""ServiceNow endpoint and parameter policy.

This is the application layer's knowledge of *what* to call, kept apart from
the adapters' knowledge of *how* to call it. Keeping URL and query-parameter
construction here is what lets the Dependency Rule hold: the use cases never
import a transport, and the transport never knows what a CMDB traversal means.
"""

from __future__ import annotations

from typing import Any, Mapping

from snowmcp.domain.records import Query, TableRef

API = "/api/now"

# Tables that carry the instance's own automation code.
CODE_TABLES: Mapping[str, str] = {
    "business_rule": "sys_script",
    "client_script": "sys_script",
    "script_include": "sys_script",
    "server_script": "sys_script",
    "ui_policy": "sys_ui_policy",
    "ui_action": "sys_ui_action",
    "ui_script": "sys_script",
    "flow": "sys_flow",
    "scripted_rest": "sys_script",
    "scheduled_job": "sys_script",
    "acl": "sys_security_acl",
    "portal_widget": "sp_widget",
    "data_source": "sp_data_source",
    "transform_map": "sys_transform_map",
    "rest_message_function": "sys_rest_message_fn",
}

# The script table distinguishes script kinds by `type` and `category`.
SCRIPT_TYPE_BY_ARTEFACT: Mapping[str, str] = {
    "business_rule": "business rule",
    "client_script": "client script",
    "script_include": "script include",
    "server_script": "server script",
    "scheduled_job": "scheduled job execution",
    "scripted_rest": "scripted rest api",
    "ui_script": "ui script",
}


def table_path(table: str) -> str:
    """The Table API path for a table."""
    return f"{API}/table/{TableRef(table).name}"


def record_path(table: str, sys_id: str) -> str:
    """The Table API path for one record."""
    return f"{table_path(table)}/{sys_id}"


def stats_path(table: str) -> str:
    """The Aggregate (stats) API path for a table."""
    return f"{API}/stats/{TableRef(table).name}"


def cmdb_path() -> str:
    """The CMDB API root."""
    return f"{API}/cmdb"


def cmdb_ci_path(sys_id: str) -> str:
    """The CMDB API path for one configuration item."""
    return f"{cmdb_path()}/ci/{sys_id}"


def attachment_path(sys_id: str) -> str:
    """The Attachment API path for one attachment record."""
    return f"{API}/attachment/{sys_id}"


def aggregate_api_path(table: str) -> str:
    """The Aggregate API path (distinct from the stats path)."""
    return f"{API}/aggregate/{TableRef(table).name}"


def script_path(table: str) -> str:
    """The Table API path for an artefact table (often sys_script)."""
    return table_path(table)


def query_params(query: Query) -> dict[str, str]:
    """Build the Table API query string for a query."""
    params: dict[str, str] = {"sysparm_limit": str(query.limit)}
    if query.encoded_query:
        params["sysparm_query"] = query.encoded_query
    if query.fields:
        params["sysparm_fields"] = ",".join(query.fields)
    if query.offset:
        params["sysparm_offset"] = str(query.offset)
    if query.order_by:
        params["sysparm_order_by"] = query.order_by
    if query.display_value:
        params["sysparm_display_value"] = "true"
    if query.aggregate:
        params["sysparm_aggregate"] = query.aggregate
    if query.group_by:
        params["sysparm_group_by"] = query.group_by
    return params


def stats_params(
    aggregate: str,
    *,
    encoded_query: str = "",
    group_by: str = "",
    group_by_2: str = "",
) -> dict[str, str]:
    """Build the Aggregate (stats) API query string."""
    params: dict[str, str] = {"sysparm_aggregate": aggregate}
    if encoded_query:
        params["sysparm_query"] = encoded_query
    if group_by:
        params["sysparm_group_by"] = group_by
    if group_by_2:
        params["sysparm_group_by_2"] = group_by_2
    return params


def cmdb_relations_params(sys_id: str, *, direction: str = "both", depth: int = 1) -> dict[str, str]:
    """Build the CMDB relationship query for one CI."""
    params: dict[str, str] = {"sysparm_query": f"parent={sys_id}^ORchild={sys_id}"}
    if direction != "both":
        params["sysparm_query"] = f"parent={sys_id}" if direction == "down" else f"child={sys_id}"
    params["sysparm_limit"] = str(max(1, depth) * 100)
    return params


def where_used_params(field_name: str) -> dict[str, str]:
    """Query parameters finding every field reference to a dictionary field."""
    return {
        "sysparm_query": f"element_reference_name={field_name}^ORname={field_name}",
        "sysparm_limit": "200",
    }


def script_search_params(text: str, *, script_type: str = "", limit: int = 50) -> dict[str, str]:
    """Query parameters for searching the instance's own code."""
    query = f"scriptLIKE{text}^ORnameLIKE{text}^ORdescriptionLIKE{text}"
    if script_type:
        query += f"^type={script_type}"
    return {"sysparm_query": query, "sysparm_limit": str(limit)}


def batch_body(operations: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a Batch API request body."""
    return {"batch_request_id": None, "operations": list(operations)}


def table_list_params(pattern: str = "", *, limit: int = 200) -> dict[str, str]:
    """Query parameters listing the tables on an instance."""
    query = f"nameLIKE{pattern}" if pattern else ""
    params = {"sysparm_limit": str(limit)}
    if query:
        params["sysparm_query"] = query
    return params
