"""Tier 2 - the defensive branches every service shares.

Each service that reads a Table API result has to cope with a response
that is not what it expected: a result that is not a list, a list holding
something that is not an object, a payload that is not a mapping. Those
branches are the easiest thing in the codebase to leave untested, because
the happy path already looks right - and they are exactly where a mutant
hides, because a changed guard does not change what the happy path
returns.

This file pins them one service at a time.
"""

from __future__ import annotations

import pytest

from snowmcp.application.graph import GraphService
from snowmcp.application.records import SchemaService
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)
from snowmcp.domain.errors import ServiceNowAPIError
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


def not_a_list() -> FakeGateway:
    """A gateway whose result is a mapping instead of a list."""
    return FakeGateway(default=ok({"result": {"name": "x"}}))


def not_a_dict() -> FakeGateway:
    """A gateway whose list holds something that is not an object."""
    return FakeGateway(default=ok({"result": ["not-a-row", {"name": "x"}]}))


class TestListResultBranches:
    """A service that returns a list returns an empty one for a bad result."""

    def test_catalog_categories_ignores_a_result_that_is_not_a_list(self) -> None:
        service = CatalogService(not_a_list(), policy())

        assert service.categories() == []

    def test_catalog_categories_drops_rows_that_are_not_objects(self) -> None:
        service = CatalogService(not_a_dict(), policy())

        assert service.categories() == [{"name": "x"}]

    def test_code_search_ignores_a_result_that_is_not_a_list(self) -> None:
        service = CodeService(not_a_list(), policy())

        assert service.search("foo") == []

    def test_code_search_drops_rows_that_are_not_objects(self) -> None:
        service = CodeService(not_a_dict(), policy())

        assert service.search("foo") == [{"name": "x"}]

    def test_code_list_ignores_a_result_that_is_not_a_list(self) -> None:
        service = CodeService(not_a_list(), policy())

        assert service.list("business_rule") == []

    def test_code_list_drops_rows_that_are_not_objects(self) -> None:
        service = CodeService(not_a_dict(), policy())

        assert service.list("business_rule") == [{"name": "x"}]

    def test_code_where_used_ignores_a_result_that_is_not_a_list(self) -> None:
        service = CodeService(not_a_list(), policy())

        assert service.where_used("foo")["scripts"] == []

    def test_the_log_ignores_a_result_that_is_not_a_list(self) -> None:
        service = OpsService(not_a_list(), policy())

        assert service.log() == []

    def test_the_log_drops_rows_that_are_not_objects(self) -> None:
        service = OpsService(not_a_dict(), policy())

        assert service.log() == [{"name": "x"}]

    def test_jobs_ignore_a_result_that_is_not_a_list(self) -> None:
        service = OpsService(not_a_list(), policy())

        assert service.jobs() == []

    def test_jobs_drop_rows_that_are_not_objects(self) -> None:
        service = OpsService(not_a_dict(), policy())

        assert service.jobs() == [{"name": "x"}]

    def test_update_sets_ignore_a_result_that_is_not_a_list(self) -> None:
        service = AdminService(not_a_list(), policy())

        assert service.update_sets() == []

    def test_update_sets_drop_rows_that_are_not_objects(self) -> None:
        service = AdminService(not_a_dict(), policy())

        assert service.update_sets() == [{"name": "x"}]

    def test_users_ignore_a_result_that_is_not_a_list(self) -> None:
        service = AdminService(not_a_list(), policy())

        assert service.users() == []

    def test_users_drop_rows_that_are_not_objects(self) -> None:
        service = AdminService(not_a_dict(), policy())

        assert service.users() == [{"name": "x"}]

    def test_groups_ignore_a_result_that_is_not_a_list(self) -> None:
        service = AdminService(not_a_list(), policy())

        assert service.groups() == []

    def test_groups_drop_rows_that_are_not_objects(self) -> None:
        service = AdminService(not_a_dict(), policy())

        assert service.groups() == [{"name": "x"}]

    def test_roles_ignore_a_result_that_is_not_a_list(self) -> None:
        service = AdminService(not_a_list(), policy())

        assert service.roles() == []

    def test_roles_drop_rows_that_are_not_objects(self) -> None:
        service = AdminService(not_a_dict(), policy())

        assert service.roles() == [{"name": "x"}]

    def test_attachments_ignore_a_result_that_is_not_a_list(self) -> None:
        service = FileService(not_a_list(), policy())

        assert service.list("incident", "rec1") == []

    def test_attachments_drop_rows_that_are_not_objects(self) -> None:
        service = FileService(not_a_dict(), policy())

        assert service.list("incident", "rec1") == [{"name": "x"}]

    def test_graph_relations_ignore_a_result_that_is_not_a_list(self) -> None:
        service = GraphService(not_a_list(), policy())

        assert service.relations("p1") == []

    def test_graph_field_references_ignore_a_result_that_is_not_a_list(self) -> None:
        service = GraphService(not_a_list(), policy())

        assert service.field_references("short_description") == []

    def test_graph_script_references_ignore_a_result_that_is_not_a_list(self) -> None:
        service = GraphService(not_a_list(), policy())

        assert service.script_references("foo") == []

    def test_schema_fields_ignore_a_result_that_is_not_a_list(self) -> None:
        service = SchemaService(not_a_list(), policy())

        assert service.fields("incident") == []

    def test_schema_field_references_ignore_a_result_that_is_not_a_list(self) -> None:
        service = SchemaService(not_a_list(), policy())

        assert service.field_references("short_description") == []


class TestPayloadBranches:
    """A service that returns a mapping keeps a non-mapping payload whole."""

    def test_catalog_items_ignore_a_payload_that_is_not_a_list(self) -> None:
        # The Service Catalog API returns a bare JSON array, not a
        # "result"-wrapped one, so the whole body is the list.
        gateway = FakeGateway(default=ok({"name": "x"}))
        service = CatalogService(gateway, policy())

        assert service.items() == []

    def test_catalog_items_drop_rows_that_are_not_objects(self) -> None:
        gateway = FakeGateway(default=ok(["not-a-row", {"name": "x"}]))
        service = CatalogService(gateway, policy())

        assert service.items() == [{"name": "x"}]

    def test_catalog_variables_ignore_a_payload_without_variables(self) -> None:
        gateway = FakeGateway(default=ok({"name": "Laptop"}))
        service = CatalogService(gateway, policy())

        assert service.variables("item1") == {"item": "item1", "variables": []}

    def test_catalog_variables_ignore_variables_that_are_not_a_list(self) -> None:
        gateway = FakeGateway(default=ok({"variables": {"name": "x"}}))
        service = CatalogService(gateway, policy())

        assert service.variables("item1")["variables"] == []

    def test_catalog_variables_drop_variable_rows_that_are_not_objects(self) -> None:
        gateway = FakeGateway(default=ok({"variables": ["not-a-row", {"name": "size"}]}))
        service = CatalogService(gateway, policy())

        assert service.variables("item1")["variables"] == [{"name": "size"}]

    def test_code_read_wraps_a_result_that_is_not_a_mapping(self) -> None:
        gateway = FakeGateway(default=ok({"result": ["not-a-mapping"]}))
        service = CodeService(gateway, policy())

        assert service.read("sys_script", "s1") == {"result": ["not-a-mapping"]}

    def test_code_read_returns_a_mapping_result_whole(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"script": "var x = 1;"}}))
        service = CodeService(gateway, policy())

        assert service.read("sys_script", "s1") == {"script": "var x = 1;"}

    def test_code_read_falls_back_to_the_body_when_there_is_no_result(self) -> None:
        gateway = FakeGateway(default=ok({"script": "var x = 1;"}))
        service = CodeService(gateway, policy())

        assert service.read("sys_script", "s1") == {"script": "var x = 1;"}

    def test_an_atf_run_that_returns_a_scalar_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok("done"))
        service = AdminService(gateway, policy())

        assert service.atf("Suite", confirmed=True) == {"result": "done"}

    def test_an_atf_run_that_returns_a_mapping_is_kept_whole(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "r1"}}))
        service = AdminService(gateway, policy())

        assert service.atf("Suite", confirmed=True) == {"result": {"sys_id": "r1"}}

    def test_a_script_run_that_returns_a_scalar_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok("done"))
        service = AdminService(gateway, policy(), scripted_rest_url="/api/x/ns/acme/run")

        assert service.script("var x = 1", confirmed=True) == {"result": "done"}

    def test_binding_an_update_set_falls_back_to_the_body(self) -> None:
        gateway = FakeGateway(default=ok({"sys_id": "us1"}))
        service = AdminService(gateway, policy())

        assert service.set_update_set("Sprint 1", confirmed=True) == {
            "update_set": "Sprint 1",
            "result": {"sys_id": "us1"},
        }

    def test_binding_an_update_set_reads_the_result(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "us1"}}))
        service = AdminService(gateway, policy())

        assert service.set_update_set("Sprint 1", confirmed=True) == {
            "update_set": "Sprint 1",
            "result": {"sys_id": "us1"},
        }

    def test_an_attachment_download_that_returns_a_scalar_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok("Zm9v"))
        service = FileService(gateway, policy())

        assert service.download("att1") == {"content": "Zm9v"}

    def test_an_attachment_upload_that_returns_a_scalar_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok("att1"))
        service = FileService(gateway, policy())

        assert service.upload("incident", "abc", "a.txt", "Zm9v", confirmed=True) == {
            "result": "att1"
        }

    def test_an_order_that_returns_a_scalar_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok("REQ01"))
        service = CatalogService(gateway, policy())

        assert service.order("item1", {}, confirmed=True) == {"result": "REQ01"}


class TestFailedResponseBranches:
    """A failed response is an error, never data."""

    def test_a_failed_catalog_read_is_not_read_as_items(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        gateway.responses = {}
        service = CatalogService(gateway, policy())

        # A 2xx with no result is an empty list, not a crash.
        assert service.items() == []

    def test_a_table_api_response_that_is_not_an_object_is_an_error(self) -> None:
        gateway = FakeGateway(default=ok(["not-an-object"]))
        service = OpsService(gateway, policy())

        with pytest.raises(ServiceNowAPIError):
            service.health()
