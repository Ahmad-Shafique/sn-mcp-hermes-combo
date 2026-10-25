"""The MCP surface: a small number of domain tools, each with an action enum.

Every other ServiceNow MCP server found in the wild exposes 17 to 500
separate tools. That is the wrong shape for an agent: each tool's schema
competes for context, and the model has to guess which of 500 names to reach
for before it can do anything.

This server exposes eleven tools. Each carries an ``action`` enum, so one
schema covers a whole domain, and a single call can carry a whole job - the
``batch`` action applies many writes in one request rather than one call
each.

Read-only tools are annotated as such, so a client running with
``trust: untrusted`` only asks for approval on the tools that can actually
change the instance.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from snowmcp.application.container import Services
from snowmcp.domain.capabilities import (
    AdminAction,
    AggregateAction,
    CatalogAction,
    CodeAction,
    FileAction,
    GraphAction,
    LocalAction,
    RecordAction,
    SchemaAction,
    OpsAction,
)
from snowmcp.domain.errors import SnowMCPError

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
READ_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False)


def _safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Translate a domain failure into a protocol error that keeps its reason.

    The MCP SDK discards the message of any exception that is not a
    ``ToolError`` and reports a bare "Error executing tool X" instead. An
    agent that cannot tell "needs confirm=true" from a crash cannot act, so
    the domain's own vocabulary is translated here, at the boundary.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except SnowMCPError as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def build_server(services: Services) -> MCPServer:
    """Build the MCP server with every tool registered."""
    server = MCPServer(
        name="servicenow",
        title="ServiceNow Consolidated",
        version="1.0.0",
        instructions=(
            "One MCP server for a ServiceNow instance. Eleven tools, each with an "
            "'action' parameter. Read with sn_read, change with sn_write, explore the "
            "CMDB Service Graph with sn_graph, and store findings locally with sn_local. "
            "Writes need confirm=true."
        ),
    )

    @server.tool(
        name="sn_read",
        annotations=READ_ONLY,
        description=(
            "Read ServiceNow records. action=query (list records matching an encoded "
            "query), action=get (one record by sys_id), action=count (how many match). "
            "Use this instead of a separate tool per table."
        ),
    )
    @_safe
    def sn_read(
        action: Literal["query", "get", "count"] = "query",
        table: str = "",
        sys_id: str = "",
        query: str = "",
        fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "",
        display_value: bool = False,
    ) -> dict[str, Any]:
        """Read records from any table."""
        if action == RecordAction.GET.value:
            record = services.records.get(table, sys_id)
            services.history.record("sn_read", f"get {table}/{sys_id}")
            return record.to_dict()
        if action == RecordAction.COUNT.value:
            total = services.records.count(table, query)
            services.history.record("sn_read", f"count {table}")
            return {"table": table, "count": total}
        page = services.records.query(
            _query(table, query, fields, limit, offset, order_by, display_value)
        )
        services.history.record("sn_read", f"query {table} ({len(page.records)} records)")
        return {
            "table": table,
            "count": len(page.records),
            "total": page.total,
            "records": [record.to_dict() for record in page.records],
        }

    @server.tool(
        name="sn_write",
        annotations=DESTRUCTIVE,
        description=(
            "Change ServiceNow records. action=create, action=update, action=delete, "
            "or action=batch (apply many operations in ONE request). Every write needs "
            "confirm=true, and every write is journalled so it can be reverted."
        ),
    )
    @_safe
    def sn_write(
        action: Literal["create", "update", "delete", "batch"] = "create",
        table: str = "",
        sys_id: str = "",
        fields: dict[str, Any] | None = None,
        operations: list[dict[str, Any]] | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Create, update or delete records."""
        payload = fields or {}
        if action == RecordAction.CREATE.value:
            record = services.records.create(table, payload, confirmed=confirm)
            services.history.record("sn_write", f"created {table}/{record.sys_id}")
            return record.to_dict()
        if action == RecordAction.UPDATE.value:
            record = services.records.update(table, sys_id, payload, confirmed=confirm)
            services.history.record("sn_write", f"updated {table}/{sys_id}")
            return record.to_dict()
        if action == RecordAction.DELETE.value:
            result = services.records.delete(table, sys_id, confirmed=confirm)
            services.history.record("sn_write", f"deleted {table}/{sys_id}")
            return result
        results = services.records.batch(operations or [], confirmed=confirm)
        services.history.record("sn_write", f"batched {len(results)} operations")
        return {"count": len(results), "results": results}

    @server.tool(
        name="sn_aggregate",
        annotations=READ_ONLY,
        description=(
            "Aggregate over a table. action=stats (COUNT/SUM/AVG/MIN/MAX) or "
            "action=group (grouped statistics). One call answers 'how many', 'how "
            "many per group' without pulling records."
        ),
    )
    @_safe
    def sn_aggregate(
        action: Literal["stats", "group"] = "stats",
        table: str = "",
        aggregate: str = "COUNT",
        query: str = "",
        group_by: str = "",
        group_by_2: str = "",
    ) -> dict[str, Any]:
        """Run aggregate statistics."""
        rows = services.aggregate.stats(
            table,
            aggregate,
            encoded_query=query,
            group_by=group_by,
            group_by_2=group_by_2,
        )
        services.history.record("sn_aggregate", f"{aggregate} on {table}")
        return {"table": table, "aggregate": aggregate, "count": len(rows), "rows": rows}

    @server.tool(
        name="sn_schema",
        annotations=READ_ONLY,
        description=(
            "Introspect the instance's data model. action=tables (list tables), "
            "action=fields (a table's dictionary entries), action=class (a CMDB class "
            "definition), action=references (who references a field)."
        ),
    )
    @_safe
    def sn_schema(
        action: Literal["tables", "fields", "class", "references"] = "fields",
        table: str = "",
        name: str = "",
        pattern: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Read table and field metadata."""
        target = table or name
        if action == SchemaAction.TABLES.value:
            rows = services.schema.tables(pattern, limit=limit)
            return {"count": len(rows), "tables": rows}
        if action == SchemaAction.FIELDS.value:
            rows = services.schema.fields(target, limit=limit)
            return {"table": target, "count": len(rows), "fields": rows}
        if action == SchemaAction.CLASS.value:
            return services.schema.class_info(target)
        rows = services.schema.field_references(target)
        return {"field": target, "count": len(rows), "references": rows}

    @server.tool(
        name="sn_graph",
        annotations=READ_ONLY,
        description=(
            "Work the CMDB Service Graph. action=relations (a CI's edges), "
            "action=traverse (walk outward), action=dependents (what breaks if this CI "
            "goes away), action=impact (what depends on a table, field or script), "
            "action=csdm (the Common Service Data Model domains)."
        ),
    )
    @_safe
    def sn_graph(
        action: Literal["relations", "traverse", "impact", "dependents", "csdm"] = "relations",
        sys_id: str = "",
        target: str = "",
        direction: Literal["both", "down", "up"] = "both",
        depth: int = 1,
        kind: Literal["auto", "table", "field", "script"] = "auto",
        model: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Traverse and analyse the CMDB graph."""
        if action == GraphAction.RELATIONS.value:
            relations = services.graph.relations(sys_id, direction=direction, limit=limit)
            return {"sys_id": sys_id, "count": len(relations), "relations": [r.__dict__ for r in relations]}
        if action == GraphAction.TRAVERSE.value:
            nodes = services.graph.traverse(sys_id, direction=direction, depth=depth, limit=limit)
            return {"sys_id": sys_id, "count": len(nodes), "nodes": [n.__dict__ for n in nodes]}
        if action == GraphAction.DEPENDENTS.value:
            nodes = services.graph.dependents(sys_id, depth=depth)
            return {"sys_id": sys_id, "count": len(nodes), "nodes": [n.__dict__ for n in nodes]}
        if action == GraphAction.CSDM.value:
            if model:
                return services.graph.csdm_context(model)
            return services.graph.csdm_models()
        return services.graph.impact(target, kind=kind)

    @server.tool(
        name="sn_catalog",
        annotations=READ_WRITE,
        description=(
            "Service Catalog. action=items (browse), action=categories, "
            "action=variables (an item's form fields), action=order (submit an order - "
            "needs confirm=true)."
        ),
    )
    @_safe
    def sn_catalog(
        action: Literal["items", "categories", "variables", "order"] = "items",
        category: str = "",
        text: str = "",
        item: str = "",
        variables: dict[str, Any] | None = None,
        quantity: int = 1,
        confirm: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Browse and order from the Service Catalog."""
        if action == CatalogAction.ITEMS.value:
            rows = services.catalog.items(category=category, text=text, limit=limit)
            return {"count": len(rows), "items": rows}
        if action == CatalogAction.CATEGORIES.value:
            rows = services.catalog.categories(limit=limit)
            return {"count": len(rows), "categories": rows}
        if action == CatalogAction.VARIABLES.value:
            return services.catalog.variables(item)
        result = services.catalog.order(item, variables or {}, quantity=quantity, confirmed=confirm)
        services.history.record("sn_catalog", f"ordered catalog item {item}")
        return result

    @server.tool(
        name="sn_files",
        annotations=READ_WRITE,
        description=(
            "Record attachments. action=list, action=download, action=upload (needs "
            "confirm=true), action=delete (needs confirm=true)."
        ),
    )
    @_safe
    def sn_files(
        action: Literal["list", "upload", "download", "delete"] = "list",
        table: str = "",
        sys_id: str = "",
        name: str = "",
        content_base64: str = "",
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Manage attachments."""
        if action == FileAction.LIST.value:
            rows = services.files.list(table, sys_id)
            return {"count": len(rows), "attachments": rows}
        if action == FileAction.DOWNLOAD.value:
            return services.files.download(sys_id)
        if action == FileAction.UPLOAD.value:
            result = services.files.upload(
                table, sys_id, name, content_base64, confirmed=confirm
            )
            services.history.record("sn_files", f"uploaded {name} to {table}/{sys_id}")
            return result
        result = services.files.delete(sys_id, confirmed=confirm)
        services.history.record("sn_files", f"deleted attachment {sys_id}")
        return result

    @server.tool(
        name="sn_code",
        annotations=READ_ONLY,
        description=(
            "Find the instance's own automation. action=search (scripts mentioning a "
            "string), action=list (artefacts of a kind), action=read (one artefact), "
            "action=where_used (every reference to a name, in code and in the schema)."
        ),
    )
    @_safe
    def sn_code(
        action: Literal["search", "list", "read", "where_used"] = "search",
        text: str = "",
        artefact: str = "",
        table: str = "",
        sys_id: str = "",
        name: str = "",
        scope: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search and read the instance's code."""
        if action == CodeAction.SEARCH.value:
            rows = services.code.search(text, artefact=artefact, limit=limit)
            return {"count": len(rows), "results": rows}
        if action == CodeAction.LIST.value:
            rows = services.code.list(artefact, limit=limit)
            return {"artefact": artefact, "count": len(rows), "results": rows}
        if action == CodeAction.READ.value:
            return services.code.read(table, sys_id)
        return services.code.where_used(name, scope=scope, limit=limit)

    @server.tool(
        name="sn_ops",
        annotations=READ_ONLY,
        description=(
            "Instance operations. action=log (system log), action=health (version and "
            "key stats), action=jobs (scheduler queue), action=properties (system "
            "properties, secrets masked), action=stats (aggregate counts)."
        ),
    )
    @_safe
    def sn_ops(
        action: Literal["log", "health", "jobs", "properties", "stats"] = "health",
        level: str = "",
        source: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Read instance health and logs."""
        if action == OpsAction.LOG.value:
            rows = services.ops.log(level=level, source=source, limit=limit)
            return {"count": len(rows), "entries": rows}
        if action == OpsAction.HEALTH.value:
            return services.ops.health()
        if action == OpsAction.JOBS.value:
            rows = services.ops.jobs(limit=limit)
            return {"count": len(rows), "jobs": rows}
        if action == OpsAction.PROPERTIES.value:
            rows = services.ops.properties(limit=limit)
            return {"count": len(rows), "properties": rows}
        return services.ops.stats()

    @server.tool(
        name="sn_local",
        annotations=READ_WRITE,
        description=(
            "The server's own memory, all local. action=note_write, action=note_read, "
            "action=note_search, action=note_list, action=note_delete, action=cache_put, "
            "action=cache_get, action=cache_list, action=saved_save, action=saved_run, "
            "action=saved_list, action=history, action=journal, action=undo."
        ),
    )
    @_safe
    def sn_local(
        action: Literal[
            "note_write", "note_read", "note_search", "note_list", "note_delete",
            "cache_put", "cache_get", "cache_list",
            "saved_save", "saved_run", "saved_list",
            "history", "journal", "undo",
        ] = "note_list",
        key: str = "",
        title: str = "",
        body: str = "",
        tags: list[str] | None = None,
        table: str = "",
        sys_id: str = "",
        payload: dict[str, Any] | None = None,
        name: str = "",
        encoded_query: str = "",
        fields: list[str] | None = None,
        limit: int = 100,
        entry_id: str = "",
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Use the server's local knowledge base, cache and journal."""
        if action == "note_write":
            note = services.knowledge.write(key, title, body, tags)
            return note.to_dict()
        if action == "note_read":
            return services.knowledge.read(key).to_dict()
        if action == "note_search":
            notes = services.knowledge.search(body or key)
            return {"count": len(notes), "notes": [note.to_dict() for note in notes]}
        if action == "note_list":
            notes = services.knowledge.list()
            return {"count": len(notes), "notes": [note.to_dict() for note in notes]}
        if action == "note_delete":
            return {"deleted": services.knowledge.delete(key), "key": key}
        if action == "cache_put":
            record = services.cache.put(table, sys_id, payload or {})
            return record.to_dict()
        if action == "cache_get":
            record = services.cache.get(table, sys_id)
            return record.to_dict() if record else {"found": False}
        if action == "cache_list":
            records = services.cache.list(table)
            return {"count": len(records), "records": [record.to_dict() for record in records]}
        if action == "saved_save":
            query = services.saved_queries.save(
                name, table, encoded_query=encoded_query, fields=fields or [], limit=limit
            )
            return query.to_dict()
        if action == "saved_run":
            return services.saved_queries.run(name)
        if action == "saved_list":
            queries = services.saved_queries.list()
            return {"count": len(queries), "queries": [query.to_dict() for query in queries]}
        if action == "history":
            calls = services.history.list(limit)
            return {"count": len(calls), "calls": [call.to_dict() for call in calls]}
        if action == "journal":
            views = services.undo.list(limit)
            return {"count": len(views), "entries": [view.to_dict() for view in views]}
        return services.undo.undo(entry_id, confirmed=confirm)

    @server.tool(
        name="sn_admin",
        annotations=READ_WRITE,
        description=(
            "Administrative surfaces. action=update_sets, action=set_update_set (bind "
            "writes to an update set - needs confirm=true), action=script (run a "
            "server-side script - needs confirm=true), action=atf (run tests - needs "
            "confirm=true), action=users, action=groups, action=roles, "
            "action=memberships."
        ),
    )
    @_safe
    def sn_admin(
        action: Literal[
            "update_sets", "set_update_set", "script", "atf",
            "users", "groups", "roles", "memberships",
        ] = "update_sets",
        update_set: str = "",
        script: str = "",
        suite: str = "",
        text: str = "",
        group: str = "",
        confirm: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Update sets, scripts, tests and the user directory."""
        if action == AdminAction.UPDATE_SETS.value:
            rows = services.admin.update_sets(limit=limit)
            return {"count": len(rows), "update_sets": rows}
        if action == AdminAction.SET_UPDATE_SET.value:
            return services.admin.set_update_set(update_set, confirmed=confirm)
        if action == AdminAction.SCRIPT.value:
            return services.admin.script(script, confirmed=confirm)
        if action == AdminAction.ATF.value:
            return services.admin.atf(suite, confirmed=confirm)
        if action == AdminAction.USERS.value:
            rows = services.admin.users(text=text, limit=limit)
            return {"count": len(rows), "users": rows}
        if action == AdminAction.GROUPS.value:
            rows = services.admin.groups(text=text, limit=limit)
            return {"count": len(rows), "groups": rows}
        if action == AdminAction.ROLES.value:
            rows = services.admin.roles(text=text, limit=limit)
            return {"count": len(rows), "roles": rows}
        return services.admin.memberships(group)

    return server


def _query(
    table: str,
    encoded_query: str,
    fields: list[str] | None,
    limit: int,
    offset: int,
    order_by: str,
    display_value: bool,
):
    """Build a validated domain query from loose tool arguments."""
    from snowmcp.domain.records import Query

    return Query(
        table=table,
        encoded_query=encoded_query,
        fields=tuple(fields or ()),
        limit=limit,
        offset=offset,
        order_by=order_by,
        display_value=display_value,
    )
