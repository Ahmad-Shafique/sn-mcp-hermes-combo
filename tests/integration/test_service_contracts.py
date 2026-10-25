"""Tier 2 - contract tests for the domain services.

Same purpose as the record contracts: assert the exact request each service
makes, so a changed limit, a dropped filter or a wrong endpoint fails here
rather than in production.
"""

from __future__ import annotations

import pytest

from snowmcp.application.graph import GraphService
from snowmcp.application.ports import Response
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)
from snowmcp.domain.errors import ConfigurationError, ServiceNowAPIError, ValidationError
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestCatalogContract:
    """The Service Catalog requests."""

    def test_items_asks_the_catalog_api_with_the_documented_parameters(self) -> None:
        gateway = FakeGateway(default=ok([{"name": "Laptop"}]))
        service = CatalogService(gateway, policy())

        service.items(category="hardware", text="Lap", catalog="c1", limit=20)

        call = gateway.last()
        assert call.path == "/api/sn_sc/servicecatalog/items"
        assert call.params == {
            "sysparm_limit": "20",
            "sysparm_category": "hardware",
            "sysparm_text": "Lap",
            "sysparm_catalog": "c1",
        }

    def test_categories_asks_the_sc_category_table(self) -> None:
        gateway = FakeGateway(default=records({"title": "Services"}))
        service = CatalogService(gateway, policy())

        service.categories(limit=15)

        call = gateway.last()
        assert call.path == "/api/now/table/sc_category"
        assert call.params == {"sysparm_limit": "15"}

    def test_variables_asks_the_catalog_item_in_the_desktop_view(self) -> None:
        gateway = FakeGateway(default=ok({"name": "Laptop", "variables": []}))
        service = CatalogService(gateway, policy())

        service.variables("item1")

        call = gateway.last()
        assert call.path == "/api/sn_sc/servicecatalog/items/item1"
        assert call.params == {"sysparm_view": "desktop"}

    def test_order_posts_the_quantity_and_the_variables(self) -> None:
        gateway = FakeGateway(default=ok({"number": "REQ01"}))
        service = CatalogService(gateway, policy())

        service.order("item1", {"size": "M"}, quantity=3, confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/sn_sc/servicecatalog/items/item1/order_now"
        assert call.json_body == {"quantity": "3", "sysparm_quantity": "3", "size": "M"}


class TestFileContract:
    """The attachment requests."""

    def test_list_asks_for_the_attachments_of_one_record(self) -> None:
        gateway = FakeGateway(default=records({"file_name": "a.png"}))
        service = FileService(gateway, policy())

        service.list("incident", "abc")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_attachment"
        assert call.params["sysparm_query"] == "table=incident^ORtable_name=incident^ORrecord_id=abc"

    def test_upload_posts_the_file_to_the_attachment_api(self) -> None:
        gateway = FakeGateway(default=ok({"sys_id": "att1"}))
        service = FileService(gateway, policy())

        service.upload("incident", "abc", "a.txt", "Zm9v", confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/attachment"
        assert call.params == {"table_name": "incident", "sys_id": "abc"}
        assert call.json_body == {
            "table_name": "incident",
            "file_name": "a.txt",
            "content": "Zm9v",
            "sysparm_type": "file",
        }

    def test_download_asks_for_one_attachment(self) -> None:
        gateway = FakeGateway(default=ok({"content": "Zm9v"}))
        service = FileService(gateway, policy())

        service.download("att1")

        call = gateway.last()
        assert call.path == "/api/now/attachment/att1"
        assert call.params == {"x": "1"}

    def test_delete_deletes_one_attachment(self) -> None:
        gateway = FakeGateway(default=ok({}))
        service = FileService(gateway, policy())

        service.delete("att1", confirmed=True)

        assert gateway.last().method == "DELETE"
        assert gateway.last().path == "/api/now/attachment/att1"


class TestCodeContract:
    """The code-discovery requests."""

    def test_search_asks_sys_script_for_every_mention(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = CodeService(gateway, policy())

        service.search("Needle", limit=10)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_script"
        assert call.params["sysparm_query"] == (
            "scriptLIKENeedle^ORnameLIKENeedle^ORdescriptionLIKENeedle"
        )
        assert call.params["sysparm_limit"] == "10"

    def test_search_can_narrow_to_one_artefact_type(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = CodeService(gateway, policy())

        service.search("Needle", artefact="business_rule")

        assert "type=business rule" in gateway.last().params["sysparm_query"]

    def test_list_asks_the_artefact_table_with_its_type(self) -> None:
        gateway = FakeGateway(default=records({"name": "Rule"}))
        service = CodeService(gateway, policy())

        service.list("business_rule", limit=5)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_script"
        assert call.params == {"sysparm_limit": "5", "sysparm_query": "type=business rule"}

    def test_read_asks_for_one_artefact(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"script": "var x = 1;"}}))
        service = CodeService(gateway, policy())

        service.read("sys_script", "abc")

        assert gateway.last().path == "/api/now/table/sys_script/abc"

    def test_where_used_asks_both_the_code_and_the_schema(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = CodeService(gateway, policy())

        service.where_used("short_description", limit=7)

        assert gateway.calls[0].path == "/api/now/table/sys_script"
        assert gateway.calls[0].params["sysparm_limit"] == "7"
        assert gateway.calls[1].path == "/api/now/table/sys_dictionary"
        assert gateway.calls[1].params["sysparm_limit"] == "200"


class TestOpsContract:
    """The operations requests."""

    def test_the_log_asks_sys_log_with_its_filters(self) -> None:
        gateway = FakeGateway(default=records({"message": "oops"}))
        service = OpsService(gateway, policy())

        service.log(level="error", source="Workflow", limit=5)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_log"
        assert call.params == {
            "sysparm_limit": "5",
            "sysparm_query": "level=error^source=Workflow",
        }

    def test_health_asks_for_the_system_properties(self) -> None:
        gateway = FakeGateway(default=records({"name": "glide.sys.version", "value": "Tokyo"}))
        service = OpsService(gateway, policy())

        service.health()

        call = gateway.last()
        assert call.path == "/api/now/table/sys_properties"
        assert call.params == {"sysparm_limit": "200"}

    def test_jobs_asks_the_scheduler_queue(self) -> None:
        gateway = FakeGateway(default=records({"name": "Nightly"}))
        service = OpsService(gateway, policy())

        service.jobs(limit=6)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_schedule_job"
        assert call.params == {"sysparm_limit": "6"}

    def test_properties_asks_for_the_system_properties(self) -> None:
        gateway = FakeGateway(default=records({"name": "a", "value": "b"}))
        service = OpsService(gateway, policy())

        service.properties(limit=11)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_properties"
        assert call.params == {"sysparm_limit": "11"}


class TestAdminContract:
    """The administrative requests."""

    def test_update_sets_asks_the_update_set_table(self) -> None:
        gateway = FakeGateway(default=records({"name": "Sprint 1"}))
        service = AdminService(gateway, policy())

        service.update_sets(limit=8)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_update_set"
        assert call.params == {"sysparm_limit": "8"}

    def test_binding_an_update_set_posts_the_name(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "us1"}}))
        service = AdminService(gateway, policy())

        service.set_update_set("Sprint 1", confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/table/sys_update_set"
        assert call.json_body == {"name": "Sprint 1", "sysparm_fields": "name"}

    def test_a_script_suite_runs_through_the_atf_api(self) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = AdminService(gateway, policy())

        service.atf("Suite", confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/now/now/atf/suite/Suite/run"
        assert call.json_body == {"name": "Suite"}

    def test_the_atf_runner_without_a_suite(self) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = AdminService(gateway, policy())

        service.atf("", confirmed=True)

        assert gateway.last().path == "/api/now/now/atf/runner"

    def test_users_asks_sys_user_with_the_search_filter(self) -> None:
        gateway = FakeGateway(default=records({"user_name": "a"}))
        service = AdminService(gateway, policy())

        service.users(text="ab", limit=4)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_user"
        assert call.params == {
            "sysparm_limit": "4",
            "sysparm_query": "nameLIKEab^ORuser_nameLIKEab",
        }

    def test_groups_asks_sys_user_group_with_the_search_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "Support"}))
        service = AdminService(gateway, policy())

        service.groups(text="Sup", limit=3)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_user_group"
        assert call.params == {
            "sysparm_limit": "3",
            "sysparm_query": "nameLIKESup^ORsys_idLIKESup",
        }

    def test_roles_asks_sys_user_role_with_the_search_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "admin"}))
        service = AdminService(gateway, policy())

        service.roles(text="adm", limit=2)

        call = gateway.last()
        assert call.path == "/api/now/table/sys_user_role"
        assert call.params == {"sysparm_limit": "2", "sysparm_query": "nameLIKEadm"}

    def test_memberships_asks_the_group_member_table(self) -> None:
        gateway = FakeGateway(default=records({"member": "u1"}))
        service = AdminService(gateway, policy())

        service.memberships("Support")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_user_grmember"
        assert call.params == {"sysparm_query": "group=Support", "sysparm_limit": "500"}


class TestGraphContract:
    """The Service Graph requests."""

    def test_relations_ask_the_relationship_table_in_both_directions(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1", "type": ""}))
        service = GraphService(gateway, policy())

        service.relations("p1", direction="both", limit=9)

        call = gateway.calls[0]
        assert call.path == "/api/now/table/cmdb_rel_ci"
        assert call.params["sysparm_query"] == "parent=p1^ORchild=p1"
        assert call.params["sysparm_limit"] == "9"

    def test_dependents_walk_downward_only(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1", "type": ""}))
        service = GraphService(gateway, policy())

        service.dependents("p1", depth=1)

        query = gateway.calls[0].params["sysparm_query"]
        assert query == "parent=p1"
        assert "ORchild" not in query

    def test_script_references_ask_sys_script(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = GraphService(gateway, policy())

        service.script_references("MyScript")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_script"
        assert "scriptLIKEMyScript" in call.params["sysparm_query"]

    def test_field_references_ask_sys_dictionary(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = GraphService(gateway, policy())

        service.field_references("short_description")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_dictionary"
        assert "element_reference_name=short_description" in call.params["sysparm_query"]


class TestHealthContract:
    """Health reads two named properties out of the property list."""

    def test_health_reports_the_release_version(self) -> None:
        gateway = FakeGateway(default=records({"name": "glide.sys.version", "value": "Tokyo"}))
        service = OpsService(gateway, policy())

        assert service.health()["version"] == "Tokyo"

    def test_health_reports_the_instance_hostname(self) -> None:
        gateway = FakeGateway(
            default=records({"name": "glide.instance.hostname", "value": "acme.service-now.com"})
        )
        service = OpsService(gateway, policy())

        assert service.health()["instance"] == "acme.service-now.com"

    def test_health_leaves_an_absent_version_as_none(self) -> None:
        gateway = FakeGateway(default=records({"name": "unrelated", "value": "x"}))
        service = OpsService(gateway, policy())

        assert service.health()["version"] is None

    def test_health_ignores_a_property_row_with_no_name(self) -> None:
        gateway = FakeGateway(default=records({"value": "x"}))
        service = OpsService(gateway, policy())

        assert service.health()["properties"] == {}

    def test_health_ignores_a_property_row_that_is_not_a_dict(self) -> None:
        gateway = FakeGateway(default=ok({"result": ["nope", {"name": "a", "value": "b"}]}))
        service = OpsService(gateway, policy())

        assert service.health()["properties"] == {"a": "b"}

    def test_health_ignores_a_result_that_is_not_a_list(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"name": "glide.sys.version"}}))
        service = OpsService(gateway, policy())

        assert service.health()["properties"] == {}

    def test_health_surfaces_a_failed_response_rather_than_reporting_no_properties(
        self,
    ) -> None:
        gateway = FakeGateway(default=Response(status=500, body={"result": [{"name": "x"}]}))
        service = OpsService(gateway, policy())

        # A health check against a broken instance must report the failure.
        # Reporting "no properties" would be indistinguishable from a
        # healthy instance that happens to expose no properties.
        with pytest.raises(ServiceNowAPIError):
            service.health()


class TestPropertyMaskingContract:
    """Secret property values never leave the server."""

    def test_an_authentication_property_is_masked(self) -> None:
        gateway = FakeGateway(default=records({"name": "glide.authenticate.key", "value": "s3cret"}))
        service = OpsService(gateway, policy())

        assert service.properties()[0]["value"] == "***"

    def test_a_property_with_password_in_its_name_is_masked(self) -> None:
        gateway = FakeGateway(default=records({"name": "my.password.thing", "value": "s3cret"}))
        service = OpsService(gateway, policy())

        assert service.properties()[0]["value"] == "***"

    def test_an_ordinary_property_is_not_masked(self) -> None:
        gateway = FakeGateway(default=records({"name": "glide.sys.version", "value": "Tokyo"}))
        service = OpsService(gateway, policy())

        assert service.properties()[0]["value"] == "Tokyo"

    def test_a_property_row_that_is_not_a_dict_is_dropped(self) -> None:
        gateway = FakeGateway(default=ok({"result": ["nope", {"name": "a", "value": "b"}]}))
        service = OpsService(gateway, policy())

        assert service.properties() == [{"name": "a", "value": "b"}]


class TestScriptedRestContract:
    """Running server-side script needs a Scripted REST API on the instance."""

    def test_without_a_scripted_rest_url_the_call_is_refused(self) -> None:
        service = AdminService(FakeGateway(), policy())

        with pytest.raises(ConfigurationError):
            service.script("var x = 1", confirmed=True)

    def test_the_script_is_posted_to_the_scripted_rest_url(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"output": "1"}}))
        service = AdminService(gateway, policy(), scripted_rest_url="/api/x/ns/acme/run")

        service.script("var x = 1", confirmed=True)

        call = gateway.last()
        assert call.method == "POST"
        assert call.path == "/api/x/ns/acme/run"
        assert call.json_body == {"script": "var x = 1", "run_as_user": "system"}

    def test_the_script_response_is_returned_whole(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"output": "1"}}))
        service = AdminService(gateway, policy(), scripted_rest_url="/api/x/ns/acme/run")

        assert service.script("var x = 1", confirmed=True) == {"result": {"output": "1"}}


class TestCodeQueryContract:
    """The exact queries the code service builds."""

    def test_a_search_for_one_artefact_kind_appends_the_type(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = CodeService(gateway, policy())

        service.search("Needle", artefact="business_rule")

        assert gateway.last().params["sysparm_query"] == (
            "scriptLIKENeedle^ORnameLIKENeedle^ORdescriptionLIKENeedle^type=business rule"
        )

    def test_where_used_asks_the_script_table_for_every_mention(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = CodeService(gateway, policy())

        service.where_used("short_description")

        assert gateway.calls[0].params["sysparm_query"] == (
            "scriptLIKEshort_description^ORnameLIKEshort_description"
            "^ORdescriptionLIKEshort_description"
        )

    def test_where_used_asks_the_dictionary_for_both_reference_forms(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = CodeService(gateway, policy())

        service.where_used("short_description")

        assert gateway.calls[1].params["sysparm_query"] == (
            "element_reference_name=short_description^ORname=short_description"
        )


class TestAttachmentValidationContract:
    """An attachment is refused before it reaches the instance."""

    def test_an_upload_without_a_name_is_refused(self) -> None:
        service = FileService(FakeGateway(), policy())

        with pytest.raises(ValidationError):
            service.upload("incident", "abc", "", "Zm9v", confirmed=True)

    def test_an_upload_whose_content_is_not_base64_is_refused(self) -> None:
        service = FileService(FakeGateway(), policy())

        with pytest.raises(ValidationError):
            service.upload("incident", "abc", "a.txt", "not base64!!", confirmed=True)
