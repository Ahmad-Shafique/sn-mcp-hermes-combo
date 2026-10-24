"""Tier 1 - unit tests for the catalog, file, code, ops and admin use cases."""

from __future__ import annotations

import pytest

from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)
from snowmcp.domain.errors import ValidationError
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestCatalogService:
    """Service Catalog."""

    def test_items_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"name": "Laptop"}))
        service = CatalogService(gateway, policy())

        rows = service.items(text="Laptop")

        assert gateway.last().path == "/api/now/table/sc_cat_item"
        assert "LIKE" in gateway.last().params["sysparm_query"]
        assert rows[0]["name"] == "Laptop"

    def test_items_filter_by_category(self) -> None:
        gateway = FakeGateway(default=records({"name": "Laptop"}))
        service = CatalogService(gateway, policy())

        service.items(category="hardware")

        assert gateway.last().params["sysparm_query"] == "category=hardware"

    def test_categories_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"title": "Services"}))
        service = CatalogService(gateway, policy())

        rows = service.categories()

        assert gateway.last().path == "/api/now/table/sc_category"
        assert rows[0]["title"] == "Services"

    def test_variables_of_an_item_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"name": "size"}))
        service = CatalogService(gateway, policy())

        result = service.variables("item1")

        assert result["item"] == "item1"
        assert result["variables"][0]["name"] == "size"

    def test_ordering_posts_to_the_catalog(self) -> None:
        gateway = FakeGateway(default=ok({"number": "REQ01"}))
        service = CatalogService(gateway, policy())

        result = service.order("item1", {"size": "M"}, confirmed=True)

        assert gateway.last().path == "/api/now/sn_sc/servicecatalog/items/item1/order"
        assert result["number"] == "REQ01"


class TestFileService:
    """Attachments."""

    def test_listing_finds_the_attachments(self) -> None:
        gateway = FakeGateway(default=records({"file_name": "a.png"}))
        service = FileService(gateway, policy())

        rows = service.list("incident", "abc")

        assert gateway.last().path == "/api/now/table/sys_attachment"
        assert rows[0]["file_name"] == "a.png"

    def test_uploading_requires_a_name(self) -> None:
        service = FileService(FakeGateway(), policy())

        with pytest.raises(ValidationError, match=r"^attachment name is required$"):
            service.upload("incident", "abc", "", "Zm9v", confirmed=True)

    def test_uploading_requires_valid_base64(self) -> None:
        service = FileService(FakeGateway(), policy())

        with pytest.raises(ValidationError, match=r"^content_base64 is not valid base64$"):
            service.upload("incident", "abc", "a.txt", "not base64!!", confirmed=True)

    def test_uploading_posts_the_attachment(self) -> None:
        gateway = FakeGateway(default=ok({"sys_id": "att1"}))
        service = FileService(gateway, policy())

        result = service.upload("incident", "abc", "a.txt", "Zm9v", confirmed=True)

        assert gateway.last().path == "/api/now/attachment"
        assert result["sys_id"] == "att1"

    def test_downloading_reads_the_attachment(self) -> None:
        gateway = FakeGateway(default=ok({"content": "Zm9v"}))
        service = FileService(gateway, policy())

        result = service.download("att1")

        assert gateway.last().path == "/api/now/attachment/att1"
        assert result["content"] == "Zm9v"

    def test_downloading_a_non_dict_body_is_wrapped(self) -> None:
        gateway = FakeGateway(default=ok(["raw"]))
        service = FileService(gateway, policy())

        assert service.download("att1") == {"content": ["raw"]}

    def test_deleting_removes_the_attachment(self) -> None:
        gateway = FakeGateway(default=ok({}))
        service = FileService(gateway, policy())

        result = service.delete("att1", confirmed=True)

        assert gateway.last().method == "DELETE"
        assert result["deleted"] is True


class TestCodeService:
    """Instance code."""

    def test_searching_finds_scripts(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = CodeService(gateway, policy())

        rows = service.search("MyScript")

        assert gateway.last().path == "/api/now/table/sys_script"
        assert rows[0]["name"] == "MyScript"

    def test_searching_by_artefact_filters_on_the_script_type(self) -> None:
        gateway = FakeGateway(default=records({"name": "MyScript"}))
        service = CodeService(gateway, policy())

        service.search("x", artefact="business_rule")

        assert "type=business rule" in gateway.last().params["sysparm_query"]

    def test_listing_an_unknown_artefact_is_refused(self) -> None:
        service = CodeService(FakeGateway(), policy())

        with pytest.raises(ValidationError, match=r"^unknown artefact type: nonsense$"):
            service.list("nonsense")

    def test_listing_an_artefact_reads_its_table(self) -> None:
        gateway = FakeGateway(default=records({"name": "Policy"}))
        service = CodeService(gateway, policy())

        rows = service.list("ui_policy")

        assert gateway.last().path == "/api/now/table/sys_ui_policy"
        assert rows[0]["name"] == "Policy"

    def test_reading_an_artefact_returns_its_definition(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"script": "var x = 1;"}}))
        service = CodeService(gateway, policy())

        result = service.read("sys_script", "abc")

        assert result["script"] == "var x = 1;"

    def test_where_used_reports_code_and_structural_references(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = CodeService(gateway, policy())

        result = service.where_used("short_description", scope="global")

        assert result["name"] == "short_description"
        assert result["scope"] == "global"
        assert "scripts" in result
        assert "structural" in result


class TestOpsService:
    """Instance operations."""

    def test_the_log_is_read_with_filters(self) -> None:
        gateway = FakeGateway(default=records({"message": "oops"}))
        service = OpsService(gateway, policy())

        rows = service.log(level="error", source="Workflow")

        assert gateway.last().path == "/api/now/table/sys_log"
        assert "level=error" in gateway.last().params["sysparm_query"]
        assert rows[0]["message"] == "oops"

    def test_health_reports_the_version(self) -> None:
        gateway = FakeGateway(
            default=records(
                {
                    "name": "glide.sys.version",
                    "value": "Tokyo",
                }
            )
        )
        service = OpsService(gateway, policy())

        health = service.health()

        assert health["version"] == "Tokyo"

    def test_jobs_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"name": "Nightly"}))
        service = OpsService(gateway, policy())

        rows = service.jobs()

        assert gateway.last().path == "/api/now/table/sys_schedule_job"
        assert rows[0]["name"] == "Nightly"

    def test_properties_mask_secrets(self) -> None:
        gateway = FakeGateway(
            default=records(
                {"name": "glide.authenticate.user", "value": "admin"},
                {"name": "public.setting", "value": "visible"},
            )
        )
        service = OpsService(gateway, policy())

        properties = service.properties()

        by_name = {item["name"]: item["value"] for item in properties}
        assert by_name["glide.authenticate.user"] == "***"
        assert by_name["public.setting"] == "visible"

    def test_stats_count_the_main_tables(self) -> None:
        gateway = FakeGateway(default=ok([{"aggregate": 3}]))
        service = OpsService(gateway, policy())

        stats = service.stats()

        assert stats["counts"]["incident"] == [{"aggregate": 3}]

    def test_stats_survive_a_table_that_cannot_be_counted(self) -> None:
        def responder(method, path, **kwargs):
            if path == "/api/now/stats/incident":
                from snowmcp.application.ports import Response

                return Response(status=403, body={"error": {"message": "denied"}})
            return ok([{"aggregate": 1}])

        gateway = FakeGateway()
        gateway.request = responder  # type: ignore[method-assign]
        service = OpsService(gateway, policy())

        stats = service.stats()

        assert stats["counts"]["incident"] is None
        assert stats["counts"]["change_request"] == [{"aggregate": 1}]


class TestAdminService:
    """Administrative surfaces."""

    def test_update_sets_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"name": "Sprint 1"}))
        service = AdminService(gateway, policy())

        rows = service.update_sets()

        assert gateway.last().path == "/api/now/table/sys_update_set"
        assert rows[0]["name"] == "Sprint 1"

    def test_binding_an_update_set_requires_a_name(self) -> None:
        service = AdminService(FakeGateway(), policy())

        with pytest.raises(ValidationError, match=r"^update_set name is required$"):
            service.set_update_set("", confirmed=True)

    def test_binding_an_update_set_posts_it(self) -> None:
        gateway = FakeGateway(default=ok({"result": {"sys_id": "us1"}}))
        service = AdminService(gateway, policy())

        result = service.set_update_set("Sprint 1", confirmed=True)

        assert gateway.last().path == "/api/now/table/sys_update_set"
        assert result["update_set"] == "Sprint 1"

    def test_running_a_script_posts_to_the_script_api(self) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = AdminService(gateway, policy())

        service.script("var x = 1;", confirmed=True)

        assert gateway.last().path == "/api/now/script"
        assert gateway.last().json_body["script"] == "var x = 1;"

    def test_running_a_test_suite_posts_to_the_atf_api(self) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = AdminService(gateway, policy())

        service.atf("Suite", confirmed=True)

        assert gateway.last().path == "/api/now/now/atf/suite/Suite/run"

    def test_running_the_test_runner_without_a_suite(self) -> None:
        gateway = FakeGateway(default=ok({"result": {}}))
        service = AdminService(gateway, policy())

        service.atf("", confirmed=True)

        assert gateway.last().path == "/api/now/now/atf/runner"

    def test_users_are_looked_up(self) -> None:
        gateway = FakeGateway(default=records({"user_name": "a"}))
        service = AdminService(gateway, policy())

        rows = service.users(text="a")

        assert gateway.last().path == "/api/now/table/sys_user"
        assert "nameLIKEa" in gateway.last().params["sysparm_query"]

    def test_groups_are_looked_up(self) -> None:
        gateway = FakeGateway(default=records({"name": "Support"}))
        service = AdminService(gateway, policy())

        rows = service.groups()

        assert gateway.last().path == "/api/now/table/sys_user_group"
        assert rows[0]["name"] == "Support"

    def test_roles_are_looked_up(self) -> None:
        gateway = FakeGateway(default=records({"name": "admin"}))
        service = AdminService(gateway, policy())

        rows = service.roles(text="admin")

        assert gateway.last().path == "/api/now/table/sys_user_role"
        assert rows[0]["name"] == "admin"

    def test_group_memberships_are_listed(self) -> None:
        gateway = FakeGateway(default=records({"member": "u1"}))
        service = AdminService(gateway, policy())

        result = service.memberships("Support")

        assert gateway.last().path == "/api/now/table/sys_user_grmember"
        assert result["group"] == "Support"
        assert result["members"][0]["member"] == "u1"
