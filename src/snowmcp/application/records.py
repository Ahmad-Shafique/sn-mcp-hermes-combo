"""Record use cases: the Table API as a domain.

Every write goes through the journal first, so any change can be reverted.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from snowmcp.application import endpoints
from snowmcp.application.ports import InstanceGateway, WriteJournal
from snowmcp.application.responses import unwrap, unwrap_list, unwrap_records
from snowmcp.domain.errors import ValidationError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Query, Record, RecordPage, TableRef
from snowmcp.domain.storage import JournalEntry


class RecordService:
    """Use cases over ServiceNow records."""

    def __init__(
        self,
        gateway: InstanceGateway,
        policy: WritePolicy,
        journal: WriteJournal | None = None,
    ) -> None:
        self._gateway = gateway
        self._policy = policy
        self._journal = journal

    def query(self, query: Query) -> RecordPage:
        """List records matching a query."""
        self._policy.check_read(query.table)
        response = self._gateway.request(
            "GET", endpoints.table_path(query.table), params=endpoints.query_params(query)
        )
        body = unwrap_records(response)
        raw_records = body.get("result")
        records = tuple(
            Record.from_payload(item, table=query.table)
            for item in (raw_records if isinstance(raw_records, list) else [])
        )
        return RecordPage(
            records=records,
            total=_as_int(body.get("total")),
            offset=query.offset,
            limit=query.limit,
        )

    def count(self, table: str, encoded_query: str = "") -> int:
        """Count records matching an encoded query."""
        self._policy.check_read(table)
        response = self._gateway.request(
            "GET",
            endpoints.table_path(table),
            params={"sysparm_query": encoded_query, "sysparm_limit": "1"},
        )
        body = unwrap_records(response)
        total = _as_int(body.get("total"))
        return total if total is not None else 0

    def get(self, table: str, sys_id: str) -> Record:
        """Fetch one record by sys_id."""
        self._policy.check_read(table)
        response = self._gateway.request(
            "GET", endpoints.record_path(table, sys_id), params={"sysparm_display_value": "true"}
        )
        body = unwrap_records(response)
        return Record.from_payload(body.get("result", body), table=table)

    def create(self, table: str, fields: Mapping[str, Any], *, confirmed: bool = False) -> Record:
        """Create a record."""
        self._policy.check_write(table, confirmed=confirmed)
        response = self._gateway.request(
            "POST", endpoints.table_path(table), json_body=dict(fields)
        )
        body = unwrap_records(response)
        record = Record.from_payload(body.get("result", body), table=table)
        self._journal_write("create", table, record.sys_id, None, record.fields)
        return record

    def update(
        self,
        table: str,
        sys_id: str,
        fields: Mapping[str, Any],
        *,
        confirmed: bool = False,
    ) -> Record:
        """Update a record's fields."""
        self._policy.check_write(table, confirmed=confirmed)
        before = self._safe_snapshot(table, sys_id)
        response = self._gateway.request(
            "PATCH", endpoints.record_path(table, sys_id), json_body=dict(fields)
        )
        body = unwrap_records(response)
        record = Record.from_payload(body.get("result", body), table=table)
        self._journal_write("update", table, sys_id, before, record.fields)
        return record

    def delete(self, table: str, sys_id: str, *, confirmed: bool = False) -> dict[str, Any]:
        """Delete a record."""
        self._policy.check_write(table, confirmed=confirmed)
        before = self._safe_snapshot(table, sys_id)
        response = self._gateway.request("DELETE", endpoints.record_path(table, sys_id))
        unwrap(response)
        self._journal_write("delete", table, sys_id, before, None)
        return {"deleted": True, "table": table, "sys_id": sys_id}

    def batch(
        self,
        operations: Sequence[Mapping[str, Any]],
        *,
        confirmed: bool = False,
    ) -> list[dict[str, Any]]:
        """Apply many writes in one request, so one tool call does the work."""
        self._policy.check_batch(len(operations))
        for operation in operations:
            table = str(operation.get("table", ""))
            verb = str(operation.get("method", "")).upper()
            if verb in ("POST", "PATCH", "PUT", "DELETE"):
                self._policy.check_write(table, confirmed=confirmed)
            else:
                self._policy.check_read(table)
        body = endpoints.batch_body(list(operations))
        response = self._gateway.request("POST", f"{endpoints.API}/batch", json_body=body)
        results = unwrap_list(response)
        for index, operation in enumerate(operations):
            verb = str(operation.get("method", "")).upper()
            if verb in ("POST", "PATCH", "PUT", "DELETE"):
                table = str(operation.get("table", ""))
                payload = operation.get("body") or {}
                sys_id = str(payload.get("sys_id", "")) if isinstance(payload, dict) else ""
                self._journal_write(verb.lower(), table, sys_id, None, payload)
        return [item for item in results if isinstance(item, dict)]

    def _safe_snapshot(self, table: str, sys_id: str) -> Mapping[str, Any] | None:
        """Read the current state of a record so a revert has something to restore."""
        try:
            response = self._gateway.request(
                "GET", endpoints.record_path(table, sys_id), params={"sysparm_display_value": "false"}
            )
        except Exception:  # noqa: BLE001 - a missing snapshot must not block the write
            return None
        if not response.ok:
            return None
        body = response.body
        return body if isinstance(body, dict) else None

    def _journal_write(
        self,
        operation: str,
        table: str,
        sys_id: str,
        before: Mapping[str, Any] | None,
        after: Mapping[str, Any] | None,
    ) -> None:
        if self._journal is None:
            return
        entry = JournalEntry(
            entry_id=f"{operation}:{table}:{sys_id}",
            operation=operation,
            table=table,
            sys_id=sys_id,
            before=before,
            after=after,
        )
        self._journal.journal_append(entry)


class AggregateService:
    """Use cases over the Aggregate (stats) API."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def stats(
        self,
        table: str,
        aggregate: str,
        *,
        encoded_query: str = "",
        group_by: str = "",
        group_by_2: str = "",
    ) -> list[dict[str, Any]]:
        """Run an aggregate over a table."""
        self._policy.check_read(table)
        params = endpoints.stats_params(
            aggregate,
            encoded_query=encoded_query,
            group_by=group_by,
            group_by_2=group_by_2,
        )
        response = self._gateway.request("GET", endpoints.stats_path(table), params=params)
        body = unwrap(response)
        if isinstance(body, dict):
            body = body.get("result", body)
        return [item for item in body if isinstance(item, dict)] if isinstance(body, list) else []


class SchemaService:
    """Use cases over table metadata."""

    def __init__(self, gateway: InstanceGateway, policy: WritePolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    def tables(self, pattern: str = "", *, limit: int = 200) -> list[dict[str, Any]]:
        """List the tables on the instance."""
        self._policy.check_read("sys_db_object")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_db_object"),
            params=endpoints.table_list_params(pattern, limit=limit),
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def fields(self, table: str, *, limit: int = 500) -> list[dict[str, Any]]:
        """List the fields of a table."""
        self._policy.check_read("sys_dictionary")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params={"sysparm_query": f"name={table}", "sysparm_limit": str(limit)},
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def class_info(self, class_name: str) -> dict[str, Any]:
        """Read the CMDB class definition for a class."""
        self._policy.check_read("cmdb_class_info")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("cmdb_class_info"),
            params={"sysparm_query": f"name={class_name}", "sysparm_limit": "1"},
        )
        body = unwrap_records(response)
        result = body.get("result")
        if isinstance(result, list) and result:
            return result[0]
        if isinstance(result, dict):
            return result
        return {}

    def field_references(self, field_name: str) -> list[dict[str, Any]]:
        """Find every dictionary reference to a field, for impact analysis."""
        self._policy.check_read("sys_dictionary")
        response = self._gateway.request(
            "GET",
            endpoints.table_path("sys_dictionary"),
            params=endpoints.where_used_params(field_name),
        )
        body = unwrap_records(response)
        result = body.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


def _as_int(value: Any) -> int | None:
    """Coerce a ServiceNow count into an int, tolerating a missing value."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
