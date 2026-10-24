"""Tier 1 - unit tests for the record, aggregate and schema use cases."""

from __future__ import annotations

import pytest

from snowmcp.application.records import AggregateService, RecordService, SchemaService
from snowmcp.application.responses import unwrap, unwrap_list, unwrap_records
from snowmcp.domain.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ServiceNowAPIError,
)
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Query
from snowmcp.application.ports import Response

from tests.conftest import FakeGateway, ok, records


def build_service(gateway: FakeGateway, policy: WritePolicy | None = None) -> RecordService:
    """A record service over the fake gateway."""
    return RecordService(gateway, policy or WritePolicy(require_confirm=False))


def test_query_builds_the_expected_request() -> None:
    gateway = FakeGateway(default=records({"sys_id": "a", "number": "INC01"}))
    service = build_service(gateway)

    page = service.query(Query(table="incident", encoded_query="state=2", limit=10))

    call = gateway.last()
    assert call.method == "GET"
    assert call.path == "/api/now/table/incident"
    assert call.params["sysparm_query"] == "state=2"
    assert call.params["sysparm_limit"] == "10"
    assert len(page.records) == 1
    assert page.records[0].sys_id == "a"


def test_query_reports_the_total_from_the_response() -> None:
    gateway = FakeGateway(default=Response(status=200, body={"result": [], "total": 42}))
    service = build_service(gateway)

    page = service.query(Query(table="incident"))

    assert page.total == 42


def test_query_tolerates_a_missing_result_key() -> None:
    gateway = FakeGateway(default=ok({"total": 3}))
    service = build_service(gateway)

    page = service.query(Query(table="incident"))

    assert len(page.records) == 0
    assert page.total == 3


def test_count_returns_the_total() -> None:
    gateway = FakeGateway(default=Response(status=200, body={"result": [], "total": 7}))
    service = build_service(gateway)

    assert service.count("incident", "state=2") == 7


def test_count_returns_zero_when_the_total_is_absent() -> None:
    gateway = FakeGateway(default=ok({"result": []}))
    service = build_service(gateway)

    assert service.count("incident") == 0


def test_get_fetches_one_record() -> None:
    gateway = FakeGateway(default=ok({"result": {"sys_id": "abc", "number": "INC01"}}))
    service = build_service(gateway)

    record = service.get("incident", "abc")

    assert gateway.last().path == "/api/now/table/incident/abc"
    assert record.sys_id == "abc"


def test_create_posts_the_fields() -> None:
    gateway = FakeGateway(default=ok({"result": {"sys_id": "new", "short_description": "x"}}))
    service = build_service(gateway)

    record = service.create("incident", {"short_description": "x"}, confirmed=True)

    call = gateway.last()
    assert call.method == "POST"
    assert call.path == "/api/now/table/incident"
    assert call.json_body == {"short_description": "x"}
    assert record.sys_id == "new"


def test_create_without_confirmation_is_refused() -> None:
    gateway = FakeGateway()
    service = build_service(gateway, WritePolicy(require_confirm=True))

    with pytest.raises(Exception, match=r"needs confirmation"):
        service.create("incident", {"short_description": "x"})


def test_update_patches_the_record() -> None:
    gateway = FakeGateway(default=ok({"result": {"sys_id": "abc"}}))
    service = build_service(gateway)

    service.update("incident", "abc", {"state": "3"}, confirmed=True)

    call = gateway.last()
    assert call.method == "PATCH"
    assert call.path == "/api/now/table/incident/abc"


def test_delete_removes_the_record() -> None:
    gateway = FakeGateway(default=ok({}))
    service = build_service(gateway)

    result = service.delete("incident", "abc", confirmed=True)

    assert gateway.last().method == "DELETE"
    assert result == {"deleted": True, "table": "incident", "sys_id": "abc"}


def test_batch_applies_many_operations_in_one_request() -> None:
    gateway = FakeGateway(default=ok({"result": [{"sys_id": "a"}, {"sys_id": "b"}]}))
    service = build_service(gateway)

    operations = [
        {"method": "POST", "table": "incident", "body": {"short_description": "one"}},
        {"method": "POST", "table": "incident", "body": {"short_description": "two"}},
    ]
    results = service.batch(operations, confirmed=True)

    assert len(gateway.calls) == 1
    assert gateway.last().path == "/api/now/batch"
    assert len(results) == 2


def test_batch_over_the_limit_is_refused() -> None:
    gateway = FakeGateway()
    service = build_service(gateway, WritePolicy(require_confirm=False, max_batch=1))

    with pytest.raises(Exception, match=r"exceeds the limit"):
        service.batch(
            [
                {"method": "POST", "table": "incident", "body": {}},
                {"method": "POST", "table": "incident", "body": {}},
            ],
            confirmed=True,
        )


def test_batch_refuses_a_read_operation_on_a_denied_table() -> None:
    gateway = FakeGateway()
    service = build_service(
        gateway, WritePolicy(require_confirm=False, denied_tables=frozenset({"sys_user"}))
    )

    with pytest.raises(Exception, match=r"denied by policy"):
        service.batch([{"method": "GET", "table": "sys_user"}], confirmed=True)


def test_a_failed_snapshot_does_not_block_the_write() -> None:
    gateway = FakeGateway(
        default=ok({"result": {"sys_id": "abc"}}),
        responses={},
    )

    def responder(method, path, **kwargs):
        if method == "GET":
            return Response(status=500, body={"error": "boom"})
        return Response(status=200, body={"result": {"sys_id": "abc"}})

    gateway.request = responder  # type: ignore[method-assign]
    service = build_service(gateway)

    record = service.update("incident", "abc", {"state": "3"}, confirmed=True)

    assert record.sys_id == "abc"


class TestResponseUnwrapping:
    """How raw responses become results or domain errors."""

    def test_a_success_returns_the_body(self) -> None:
        assert unwrap(Response(status=200, body={"ok": True})) == {"ok": True}

    def test_a_401_raises_an_authentication_error(self) -> None:
        with pytest.raises(AuthenticationError, match=r"^bad credentials$"):
            unwrap(Response(status=401, body={"error": {"message": "bad credentials"}}))

    def test_a_403_raises_a_permission_error(self) -> None:
        with pytest.raises(PermissionDeniedError, match=r"^acl denied$"):
            unwrap(Response(status=403, body={"error": {"message": "acl denied"}}))

    def test_a_404_raises_a_not_found_error(self) -> None:
        with pytest.raises(NotFoundError, match=r"^no such record$"):
            unwrap(Response(status=404, body={"error": {"message": "no such record"}}))

    def test_a_500_raises_an_api_error_carrying_the_status(self) -> None:
        with pytest.raises(ServiceNowAPIError) as caught:
            unwrap(Response(status=500, body={"error": {"message": "server exploded"}}))
        assert caught.value.status == 500

    def test_an_error_without_a_body_uses_the_status_in_the_message(self) -> None:
        with pytest.raises(ServiceNowAPIError, match=r"HTTP 502"):
            unwrap(Response(status=502, body=None))

    def test_error_detail_reads_a_plain_message_key(self) -> None:
        with pytest.raises(ServiceNowAPIError, match=r"^plain failure$"):
            unwrap(Response(status=400, body={"message": "plain failure"}))

    def test_error_detail_reads_a_string_body(self) -> None:
        with pytest.raises(ServiceNowAPIError, match=r"^raw text$"):
            unwrap(Response(status=400, body="raw text"))

    def test_unwrap_records_rejects_a_non_object_body(self) -> None:
        with pytest.raises(ServiceNowAPIError, match=r"^expected a JSON object from the Table API$"):
            unwrap_records(Response(status=200, body=["not", "an", "object"]))

    def test_unwrap_list_reads_the_result_key(self) -> None:
        assert unwrap_list(Response(status=200, body={"result": [1, 2]})) == [1, 2]

    def test_unwrap_list_reads_a_bare_array(self) -> None:
        assert unwrap_list(Response(status=200, body=[1, 2])) == [1, 2]

    def test_unwrap_list_rejects_an_unexpected_body(self) -> None:
        with pytest.raises(ServiceNowAPIError, match=r"^expected a JSON array from the API$"):
            unwrap_list(Response(status=200, body={"nope": 1}))


class TestAggregateService:
    """Aggregate statistics."""

    def test_stats_reads_the_stats_endpoint(self) -> None:
        gateway = FakeGateway(default=ok([{"group": "2", "aggregate": 5}]))
        service = AggregateService(gateway, WritePolicy(require_confirm=False))

        rows = service.stats("incident", "COUNT", encoded_query="state=2")

        assert gateway.last().path == "/api/now/stats/incident"
        assert gateway.last().params["sysparm_aggregate"] == "COUNT"
        assert rows == [{"group": "2", "aggregate": 5}]

    def test_stats_reads_a_result_wrapper(self) -> None:
        gateway = FakeGateway(default=ok({"result": [{"aggregate": 3}]}))
        service = AggregateService(gateway, WritePolicy(require_confirm=False))

        assert service.stats("incident", "COUNT") == [{"aggregate": 3}]


class TestSchemaService:
    """Table metadata."""

    def test_tables_lists_the_instance_tables(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = SchemaService(gateway, WritePolicy(require_confirm=False))

        rows = service.tables("inc")

        assert gateway.last().path == "/api/now/table/sys_db_object"
        assert rows == [{"name": "incident"}]

    def test_fields_lists_a_table_dictionary(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = SchemaService(gateway, WritePolicy(require_confirm=False))

        rows = service.fields("incident")

        assert gateway.last().params["sysparm_query"] == "name=incident"
        assert rows == [{"element_id": "x"}]

    def test_class_info_returns_the_first_match(self) -> None:
        gateway = FakeGateway(default=records({"name": "Server"}))
        service = SchemaService(gateway, WritePolicy(require_confirm=False))

        assert service.class_info("Server") == {"name": "Server"}

    def test_class_info_returns_an_empty_mapping_when_absent(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = SchemaService(gateway, WritePolicy(require_confirm=False))

        assert service.class_info("Missing") == {}

    def test_class_info_returns_a_dict_result(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"name": "Server"}}))
        service = SchemaService(gateway, WritePolicy(require_confirm=False))

        assert service.class_info("Server") == {"name": "Server"}
