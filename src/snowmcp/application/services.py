"""Catalog, attachment, code, operations and administrative use cases."""

from __future__ import annotations

import base64
from typing import Any, Mapping

from snowmcp.application import endpoints
from snowmcp.application.ports import InstanceGateway
from snowmcp.application.responses import unwrap, unwrap_records
from snowmcp.domain.errors import ConfigurationError, ValidationError
from snowmcp.domain.policy import WritePolicy

CATALOG_ITEM_TABLE = "sc_req_item"
SCTASK_TABLE = "sc_task"


def _as_dicts(payload: Any) -> list[dict[str, Any]]:
    """Read a JSON array of objects, tolerating an empty or odd response."""
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


class CatalogService:
    """Service Catalog browsing and ordering.

    The Service Catalog API has its own root (``/api/sn_sc/...``), not the
    ``/api/now/...`` the Table API lives under.
    """

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def items(
        self,
        *,
        category: str = "",
        text: str = "",
        catalog: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Browse catalog items, optionally filtered by category or text."""
        self._policy.check_read("sc_cat_item")
        response = self._gateway.request(
            "GET",
            endpoints.catalog_items_path(),
            params=endpoints.catalog_items_params(
                category=category, text=text, catalog=catalog, limit=limit
            ),
        )
        return _as_dicts(unwrap(response))

    def categories(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """List catalog categories."""
        self._policy.check_read("sc_category")
        response = self._gateway.request(
            "GET", endpoints.table_path("sc_category"), params={"sysparm_limit": str(limit)}
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def variables(self, item_sys_id: str) -> dict[str, Any]:
        """The variables (form fields) of one catalog item."""
        self._policy.check_read("sc_cat_item")
        response = self._gateway.request(
            "GET", endpoints.catalog_item_path(item_sys_id), params={"sysparm_view": "desktop"}
        )
        payload = unwrap(response)
        variables = payload.get("variables") if isinstance(payload, dict) else None
        return {
            "item": item_sys_id,
            "variables": [item for item in variables if isinstance(item, dict)]
            if isinstance(variables, list)
            else [],
        }

    def order(
        self,
        item_sys_id: str,
        variables: Mapping[str, Any],
        *,
        quantity: int = 1,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Order a catalog item."""
        self._policy.check_write(CATALOG_ITEM_TABLE, confirmed=confirmed)
        body: dict[str, Any] = {
            "quantity": str(quantity),
            "sysparm_quantity": str(quantity),
        }
        body.update({str(key): str(value) for key, value in variables.items()})
        response = self._gateway.request(
            "POST", endpoints.catalog_order_path(item_sys_id), json_body=body
        )
        payload = unwrap(response)
        return payload if isinstance(payload, dict) else {"result": payload}


class FileService:
    """Attachment operations."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def list(self, table: str, sys_id: str) -> list[dict[str, Any]]:
        """List the attachments on a record."""
        self._policy.check_read("sys_attachment")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_attachment"),
            params={"sysparm_query": f"table={table}^ORtable_name={table}^ORrecord_id={sys_id}"},
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def upload(
        self,
        table: str,
        sys_id: str,
        name: str,
        content_base64: str,
        *,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Attach a file to a record."""
        self._policy.check_write("sys_attachment", confirmed=confirmed)
        if not name:
            raise ValidationError("attachment name is required")
        try:
            base64.b64decode(content_base64, validate=True)
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
            raise ValidationError("content_base64 is not valid base64") from exc
        body = {
            "table_name": table,
            "file_name": name,
            "content": content_base64,
            "sysparm_type": "file",
        }
        response = self._gateway.request(
            "POST",
            f"{endpoints.API}/attachment",
            params={"table_name": table, "sys_id": sys_id},
            json_body=body,
        )
        payload = unwrap(response)
        return payload if isinstance(payload, dict) else {"result": payload}

    def download(self, attachment_sys_id: str) -> dict[str, Any]:
        """Download an attachment's content."""
        self._policy.check_read("sys_attachment")
        response = self._gateway.request(
            "GET", endpoints.attachment_path(attachment_sys_id), params={"x": "1"}
        )
        payload = unwrap(response)
        if isinstance(payload, dict):
            return payload
        return {"content": payload}

    def delete(self, attachment_sys_id: str, *, confirmed: bool = False) -> dict[str, Any]:
        """Delete an attachment."""
        self._policy.check_write("sys_attachment", confirmed=confirmed)
        response = self._gateway.request("DELETE", endpoints.attachment_path(attachment_sys_id))
        unwrap(response)
        return {"deleted": True, "sys_id": attachment_sys_id}


class CodeService:
    """Discovery and search across the instance's own automation code."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def search(self, text: str, *, artefact: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Search the instance's scripts for a string."""
        self._policy.check_read("sys_script")
        script_type = endpoints.SCRIPT_TYPE_BY_ARTEFACT.get(artefact, "")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_script"),
            params=endpoints.script_search_params(text, script_type=script_type, limit=limit),
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def list(self, artefact: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """List the artefacts of one kind."""
        table = endpoints.CODE_TABLES.get(artefact)
        if table is None:
            raise ValidationError(f"unknown artefact type: {artefact}")
        self._policy.check_read(table)
        params: dict[str, str] = {"sysparm_limit": str(limit)}
        script_type = endpoints.SCRIPT_TYPE_BY_ARTEFACT.get(artefact, "")
        if script_type:
            params["sysparm_query"] = f"type={script_type}"
        response = self._gateway.request("GET", endpoints.table_path(table), params=params)
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def read(self, table: str, sys_id: str) -> dict[str, Any]:
        """Read one artefact's definition."""
        self._policy.check_read(table)
        response = self._gateway.request("GET", endpoints.record_path(table, sys_id))
        body = unwrap_records(response)
        result = body.get("result", body)
        return result if isinstance(result, dict) else {"result": result}

    def where_used(self, name: str, *, scope: str = "", limit: int = 100) -> dict[str, Any]:
        """Find where a name is referenced, in code and in the schema."""
        self._policy.check_read("sys_script")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_script"),
            params=endpoints.script_search_params(name, limit=limit),
        )
        body = unwrap_records(response)
        result = body.get("result")
        scripts = [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        structural_response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params=endpoints.where_used_params(name),
        )
        structural_body = unwrap_records(structural_response)
        structural_result = structural_body.get("result")
        structural = (
            [item for item in structural_result if isinstance(item, dict)]
            if isinstance(structural_result, list)
            else []
        )
        return {"name": name, "scope": scope, "scripts": scripts, "structural": structural}


class OpsService:
    """Instance health, logs, scheduled jobs and system properties."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def log(self, *, level: str = "", source: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Read the system log."""
        self._policy.check_read("sys_log")
        query = ""
        if level:
            query = f"level={level}"
        if source:
            clause = f"source={source}"
            query = f"{query}^{clause}" if query else clause
        params: dict[str, str] = {"sysparm_limit": str(limit)}
        if query:
            params["sysparm_query"] = query
        response = self._gateway.request("GET", endpoints.table_path("sys_log"), params=params)
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def health(self) -> dict[str, Any]:
        """Version, node count and key instance statistics."""
        self._policy.check_read("sys_properties")
        response = self._gateway.request(
            "GET", endpoints.table_path("sys_properties"), params={"sysparm_limit": "200"}
        )
        body = unwrap_records(response)
        result = body.get("result")
        properties = {
            str(item.get("name")): item.get("value")
            for item in (result if isinstance(result, list) else [])
            if isinstance(item, dict) and item.get("name")
        }
        return {
            "version": properties.get("glide.sys.version"),
            "instance": properties.get("glide.instance.hostname"),
            "properties": properties,
        }

    def jobs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """The scheduler's queue."""
        self._policy.check_read("sys_schedule_job")
        response = self._gateway.request(
            "GET", endpoints.table_path("sys_schedule_job"), params={"sysparm_limit": str(limit)}
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def properties(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """System properties, with secret values masked."""
        self._policy.check_read("sys_properties")
        response = self._gateway.request(
            "GET", endpoints.table_path("sys_properties"), params={"sysparm_limit": str(limit)}
        )
        body = unwrap_records(response)
        result = body.get("result")
        properties = []
        for item in result if isinstance(result, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            value = item.get("value")
            if name.startswith("glide.authenticate.") or "password" in name.lower():
                value = "***"
            properties.append({"name": name, "value": value})
        return properties

    def stats(self) -> dict[str, Any]:
        """Aggregate counts for the most common ITSM and CMDB tables."""
        from snowmcp.application.records import AggregateService

        self._policy.check_read("sys_properties")
        service = AggregateService(self._gateway, self._policy)
        counts: dict[str, Any] = {}
        for table in ("incident", "change_request", "sys_user", "cmdb_ci"):
            try:
                counts[table] = service.stats(table, "COUNT")
            except Exception:  # noqa: BLE001 - a missing table must not break the summary
                counts[table] = None
        return {"counts": counts}


class AdminService:
    """Update sets, scripts, tests and the user directory."""

    def __init__(
        self,
        gateway: InstanceGateway,
        policy: WritePolicy,
        scripted_rest_url: str = "",
    ) -> None:
        self._gateway = gateway
        self._policy = policy
        self._scripted_rest_url = scripted_rest_url

    def update_sets(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """List the instance's update sets."""
        self._policy.check_read("sys_update_set")
        response = self._gateway.request(
            "GET", endpoints.table_path("sys_update_set"), params={"sysparm_limit": str(limit)}
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def set_update_set(self, update_set: str, *, confirmed: bool = False) -> dict[str, Any]:
        """Bind subsequent Table API writes to a named update set."""
        self._policy.check_write("sys_update_set", confirmed=confirmed)
        if not update_set:
            raise ValidationError("update_set name is required")
        response = self._gateway.request(
            "POST",
            endpoints.table_path("sys_update_set"),
            json_body={"name": update_set, "sysparm_fields": "name"},
        )
        body = unwrap_records(response)
        result = body.get("result", body)
        return {"update_set": update_set, "result": result}

    def script(self, script: str, *, confirmed: bool = False) -> dict[str, Any]:
        """Run a server-side script through a Scripted REST API.

        ServiceNow publishes **no** REST endpoint that executes arbitrary
        server-side script, so there is nothing to call directly. The
        documented route is a Scripted REST API you control on the instance;
        point ``SN_SCRIPTED_REST_URL`` at one and this calls it.
        """
        self._policy.check_write("sys_script", confirmed=confirmed)
        if not self._scripted_rest_url:
            raise ConfigurationError(
                "running server-side script needs SN_SCRIPTED_REST_URL: the path of a "
                "Scripted REST API on the instance that executes the script you send"
            )
        response = self._gateway.request(
            "POST",
            self._scripted_rest_url,
            json_body={"script": script, "run_as_user": "system"},
        )
        payload = unwrap(response)
        return payload if isinstance(payload, dict) else {"result": payload}

    def atf(self, suite: str = "", *, confirmed: bool = False) -> dict[str, Any]:
        """Run an Automated Test Framework suite."""
        self._policy.check_write("sys_atf_test", confirmed=confirmed)
        if suite:
            response = self._gateway.request(
                "POST",
                f"{endpoints.API}/now/atf/suite/{suite}/run",
                json_body={"name": suite},
            )
        else:
            response = self._gateway.request("POST", f"{endpoints.API}/now/atf/runner", json_body={})
        payload = unwrap(response)
        return payload if isinstance(payload, dict) else {"result": payload}

    def users(self, *, text: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Look up users."""
        self._policy.check_read("sys_user")
        params: dict[str, str] = {"sysparm_limit": str(limit)}
        if text:
            params["sysparm_query"] = f"nameLIKE{text}^ORuser_nameLIKE{text}"
        response = self._gateway.request("GET", endpoints.table_path("sys_user"), params=params)
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def groups(self, *, text: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Look up groups."""
        self._policy.check_read("sys_user_group")
        params: dict[str, str] = {"sysparm_limit": str(limit)}
        if text:
            params["sysparm_query"] = f"nameLIKE{text}^ORsys_idLIKE{text}"
        response = self._gateway.request("GET", endpoints.table_path("sys_user_group"), params=params)
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def roles(self, *, text: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Look up roles."""
        self._policy.check_read("sys_user_role")
        params: dict[str, str] = {"sysparm_limit": str(limit)}
        if text:
            params["sysparm_query"] = f"nameLIKE{text}"
        response = self._gateway.request("GET", endpoints.table_path("sys_user_role"), params=params)
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def memberships(self, group: str) -> dict[str, Any]:
        """The members of a group."""
        self._policy.check_read("sys_user_grmember")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_user_grmember"),
            params={"sysparm_query": f"group={group}", "sysparm_limit": "500"},
        )
        body = unwrap_records(response)
        result = body.get("result")
        members = [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        return {"group": group, "members": members}
