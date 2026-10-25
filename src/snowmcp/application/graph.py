"""Service Graph use cases: CMDB traversal, impact analysis, CSDM.

The CMDB is a graph of configuration items joined by relationships. Impact
analysis is the question that graph exists to answer: if this CI, field or
table changes, what else moves?
"""

from __future__ import annotations

from typing import Any, Mapping

from snowmcp.application import endpoints
from snowmcp.application.ports import InstanceGateway
from snowmcp.application.responses import unwrap_records
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import GraphNode, Relation


class GraphService:
    """Use cases over the CMDB Service Graph."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def relations(self, sys_id: str, *, direction: str = "both", limit: int = 200) -> list[Relation]:
        """List the relationships touching one configuration item.

        A relation row carries a relationship *type* sys_id. The type's label
        lives in ``cmdb_rel_type``, so it is resolved here - a graph of bare
        sys_ids is not something a human or an agent can read.
        """
        self._policy.check_read("cmdb_rel_ci")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("cmdb_rel_ci"),
            params=endpoints.cmdb_relations_params(sys_id, direction=direction, depth=1)
            | {"sysparm_limit": str(limit)},
        )
        body = unwrap_records(response)
        result = body.get("result")
        relations = []
        for item in result if isinstance(result, list) else []:
            if not isinstance(item, dict):
                continue
            relations.append(
                Relation(
                    parent_sys_id=str(item.get("parent", "")),
                    child_sys_id=str(item.get("child", "")),
                    type_sys_id=str(item.get("type", "")),
                    type_label=self._relation_type_label(str(item.get("type", ""))),
                    parent_table=str(item.get("parent_type", "")),
                    child_table=str(item.get("child_type", "")),
                )
            )
        return relations

    def _relation_type_label(self, type_sys_id: str) -> str:
        """Resolve a relationship type sys_id to its label."""
        if not type_sys_id:
            return ""
        self._policy.check_read("cmdb_rel_type")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("cmdb_rel_type"),
            params={"sysparm_query": f"sys_id={type_sys_id}", "sysparm_limit": "1"},
        )
        if not response.ok:
            return ""
        body = unwrap_records(response)
        result = body.get("result")
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return str(result[0].get("name", ""))
        if isinstance(result, dict):
            return str(result.get("name", ""))
        return ""

    def traverse(
        self,
        sys_id: str,
        *,
        direction: str = "both",
        depth: int = 1,
        limit: int = 500,
    ) -> list[GraphNode]:
        """Walk the Service Graph outward from a CI and return the nodes reached."""
        bounded_depth = max(1, min(depth, endpoints.MAX_TRAVERSAL_DEPTH))
        seen: set[str] = {sys_id}
        nodes: list[GraphNode] = []
        frontier = [sys_id]
        for level in range(1, bounded_depth + 1):
            next_frontier: list[str] = []
            for current in frontier:
                for relation in self.relations(current, direction=direction):
                    neighbour = (
                        relation.child_sys_id
                        if relation.parent_sys_id == current
                        else relation.parent_sys_id
                    )
                    if not neighbour or neighbour in seen:
                        continue
                    seen.add(neighbour)
                    next_frontier.append(neighbour)
                    nodes.append(
                        GraphNode(
                            sys_id=neighbour,
                            table=relation.child_table or relation.parent_table,
                            depth=level,
                        )
                    )
                    if len(nodes) >= limit:
                        return nodes
            frontier = next_frontier
            if not frontier:
                break
        return nodes

    def dependents(self, sys_id: str, *, depth: int = 1) -> list[GraphNode]:
        """Everything downstream of a CI - what breaks if it goes away."""
        return self.traverse(sys_id, direction="down", depth=depth)

    def impact(self, target: str, *, kind: str = "auto") -> dict[str, Any]:
        """Analyse what depends on a table, a field or a script.

        ``kind`` selects the lens: ``table``, ``field``, ``script`` or ``auto``
        (which inspects the target and picks).
        """
        resolved = kind if kind != "auto" else self._guess_kind(target)
        if resolved == "field":
            return {"kind": "field", "target": target, "field_references": self.field_references(target)}
        if resolved == "script":
            return {"kind": "script", "target": target, "script_references": self.script_references(target)}
        return {"kind": "table", "target": target, "table_config": self.table_config(target)}

    def _guess_kind(self, target: str) -> str:
        """Work out which impact lens fits, by asking the instance.

        A name can be a table, a field or a script, and the same string could
        in principle be more than one. The instance is the authority.
        """
        if self._is_table(target):
            return "table"
        if self._is_field(target):
            return "field"
        return "script"

    def _is_table(self, target: str) -> bool:
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_db_object"),
            params={"sysparm_query": f"name={target}", "sysparm_limit": "1"},
        )
        if not response.ok:
            return False
        body = unwrap_records(response)
        result = body.get("result")
        return bool(result)

    def _is_field(self, target: str) -> bool:
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params={"sysparm_query": f"element_reference_name={target}", "sysparm_limit": "1"},
        )
        if not response.ok:
            return False
        body = unwrap_records(response)
        result = body.get("result")
        return bool(result)

    def table_config(self, table: str) -> dict[str, Any]:
        """The schema of a table: its dictionary entries and object metadata."""
        self._policy.check_read("sys_dictionary")
        fields = self._fields_of(table)
        object_response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_db_object"),
            params={"sysparm_query": f"name={table}", "sysparm_limit": "1"},
        )
        object_body = unwrap_records(object_response)
        object_result = object_body.get("result")
        metadata: Mapping[str, Any] = {}
        if isinstance(object_result, list) and object_result:
            metadata = object_result[0]
        elif isinstance(object_result, dict):
            metadata = object_result
        return {"name": table, "fields": fields, "metadata": dict(metadata)}

    def field_references(self, field_name: str) -> list[dict[str, Any]]:
        """Every dictionary entry that references a field."""
        self._policy.check_read("sys_dictionary")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params=endpoints.where_used_params(field_name),
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def script_references(self, target: str) -> list[dict[str, Any]]:
        """Every script that mentions a name, for change impact."""
        self._policy.check_read("sys_script")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_script"),
            params=endpoints.script_search_params(target, limit=100),
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def csdm_models(self, *, limit: int = 100) -> dict[str, Any]:
        """The Common Service Data Model domains and their models.

        ``sys_csdm_domain_model`` and ``sys_csdm_context`` are *not* named in
        ServiceNow's public documentation - they may be internal tables. So
        this probes ``sys_db_object`` first and reports honestly rather than
        failing with a confusing 404.
        """
        self._policy.check_read("sys_db_object")
        if not self._table_exists("sys_csdm_domain_model"):
            return {
                "available": False,
                "reason": (
                    "the table 'sys_csdm_domain_model' is not present on this instance; "
                    "it is not part of ServiceNow's public documented contract"
                ),
                "models": [],
            }
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_csdm_domain_model"),
            params={"sysparm_limit": str(limit)},
        )
        body = unwrap_records(response)
        result = body.get("result")
        models = (
            [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        )
        return {"available": True, "models": models}

    def csdm_context(self, model: str, *, limit: int = 100) -> dict[str, Any]:
        """The contexts (graph projections) of one CSDM model."""
        self._policy.check_read("sys_db_object")
        if not self._table_exists("sys_csdm_context"):
            return {
                "available": False,
                "reason": (
                    "the table 'sys_csdm_context' is not present on this instance; "
                    "it is not part of ServiceNow's public documented contract"
                ),
                "contexts": [],
            }
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_csdm_context"),
            params={"sysparm_query": f"domain_model={model}", "sysparm_limit": str(limit)},
        )
        body = unwrap_records(response)
        result = body.get("result")
        contexts = (
            [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        )
        return {"available": True, "model": model, "contexts": contexts}

    def _table_exists(self, table: str) -> bool:
        """Ask the instance whether a table exists."""
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_db_object"),
            params={"sysparm_query": f"name={table}", "sysparm_limit": "1"},
        )
        if not response.ok:
            return False
        body = unwrap_records(response)
        return bool(body.get("result"))

    def _fields_of(self, table: str) -> list[dict[str, Any]]:
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params={"sysparm_query": f"name={table}", "sysparm_limit": "500"},
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
