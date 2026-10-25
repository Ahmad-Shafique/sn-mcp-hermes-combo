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

# The Service Catalog API is NOT under /api/now - it has its own root.
CATALOG_API = "/api/sn_sc/servicecatalog"

# ServiceNow applies sysparm_limit *before* ACL evaluation, so a limit far
# above the caller's row count can still return rows they cannot see.
MAX_TRAVERSAL_DEPTH = 10
DEFAULT_TRAVERSAL_DEPTH = 6
MAX_TRAVERSAL_NODES = 500
DEFAULT_TRAVERSAL_NODES = 250

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


def cmdb_relations_params(sys_id: str, *, direction: str = "both", limit: int = 100) -> dict[str, str]:
    """Build the CMDB relationship query for one CI.

    The relationship table has no server-side depth, so the walk is done
    on this side and the limit is simply how many rows to ask for.
    """
    params: dict[str, str] = {"sysparm_query": f"parent={sys_id}^ORchild={sys_id}"}
    if direction != "both":
        params["sysparm_query"] = f"parent={sys_id}" if direction == "down" else f"child={sys_id}"
    params["sysparm_limit"] = str(limit)
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
    """Build a Batch API request body.

    The Batch API takes ``rest_requests``, each with an id, a method and a
    *relative url* (query parameters included). A body must be Base64-encoded
    and carry its own headers. The friendly per-operation shape the caller
    uses (``table``/``body``) is translated here, so the caller never has to
    know the wire format.
    """
    import base64
    import json

    rest_requests = []
    for index, operation in enumerate(operations):
        method = str(operation.get("method", "GET")).upper()
        table = str(operation.get("table", ""))
        sys_id = str(operation.get("sys_id", ""))
        path = f"/api/now/table/{table}"
        if sys_id:
            path = f"{path}/{sys_id}"
        query = operation.get("query") or {}
        if query:
            path = f"{path}?{urlencode(query)}"
        item: dict[str, Any] = {
            "id": str(index + 1),
            "method": method,
            "url": path,
        }
        payload = operation.get("body")
        if payload is not None:
            item["body"] = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
            item["headers"] = [{"name": "Content-Type", "value": "application/json"}]
        rest_requests.append(item)
    return {"batch_request_id": None, "rest_requests": rest_requests}


def batch_path() -> str:
    """The Batch API path. The Batch API is versioned."""
    return f"{API}/v1/batch"


def catalog_items_path() -> str:
    """The Service Catalog items endpoint."""
    return f"{CATALOG_API}/items"


def catalog_item_path(item_sys_id: str) -> str:
    """One Service Catalog item."""
    return f"{CATALOG_API}/items/{item_sys_id}"


def catalog_order_path(item_sys_id: str) -> str:
    """The endpoint that submits a catalog order."""
    return f"{CATALOG_API}/items/{item_sys_id}/order_now"


def catalog_items_params(
    *, category: str = "", text: str = "", catalog: str = "", limit: int = 50
) -> dict[str, str]:
    """Query parameters for browsing the catalog."""
    params: dict[str, str] = {"sysparm_limit": str(limit)}
    if category:
        params["sysparm_category"] = category
    if text:
        params["sysparm_text"] = text
    if catalog:
        params["sysparm_catalog"] = catalog
    return params


def cmdb_meta_path(class_name: str) -> str:
    """The documented CMDB class-introspection endpoint."""
    return f"{API}/cmdb/meta/{class_name}"


def cmdb_instance_relation_path(class_name: str, sys_id: str) -> str:
    """The documented CMDB relation endpoint for one CI."""
    return f"{API}/cmdb/instance/{class_name}/{sys_id}/relation"


def urlencode(params: Mapping[str, Any]) -> str:
    """Encode query parameters for a Batch API url."""
    from urllib.parse import urlencode as _urlencode

    return _urlencode({key: str(value) for key, value in params.items()})


def table_list_params(pattern: str = "", *, limit: int = 200) -> dict[str, str]:
    """Query parameters listing the tables on an instance."""
    query = f"nameLIKE{pattern}" if pattern else ""
    params = {"sysparm_limit": str(limit)}
    if query:
        params["sysparm_query"] = query
    return params
