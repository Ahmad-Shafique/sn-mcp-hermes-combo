"""Tier 2 - the requests made when a caller passes no options.

Every contract test elsewhere passes an explicit limit, an explicit
filter, an explicit pattern. That is good practice for a test - and it
leaves the *default* value of every one of those parameters untested,
which is exactly where a mutant hides: changing ``limit: int = 200`` to
``limit: int = 100`` changes nothing about a test that always passes 30.

This file calls each method with only its required arguments and pins the
request that comes out.
"""

from __future__ import annotations

from snowmcp.application.graph import GraphService
from snowmcp.application.records import AggregateService, SchemaService
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    OpsService,
)
from snowmcp.domain.policy import WritePolicy

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


class TestSchemaDefaults:
    """The schema service's default request."""

    def test_listing_tables_asks_for_two_hundred_by_default(self) -> None:
        gateway = FakeGateway(default=records({"name": "incident"}))
        service = SchemaService(gateway, policy())

        service.tables()

        call = gateway.last()
        assert call.path == "/api/now/table/sys_db_object"
        assert call.params == {"sysparm_limit": "200"}

    def test_listing_fields_asks_for_five_hundred_by_default(self) -> None:
        gateway = FakeGateway(default=records({"element_id": "x"}))
        service = SchemaService(gateway, policy())

        service.fields("incident")

        call = gateway.last()
        assert call.path == "/api/now/table/sys_dictionary"
        assert call.params == {"sysparm_query": "name=incident", "sysparm_limit": "500"}


class TestCatalogDefaults:
    """The catalog service's default request."""

    def test_browsing_items_asks_for_fifty_with_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"sys_id": "item1"}))
        service = CatalogService(gateway, policy())

        service.items()

        call = gateway.last()
        assert call.path == "/api/sn_sc/servicecatalog/items"
        assert call.params == {"sysparm_limit": "50"}

    def test_listing_categories_asks_for_one_hundred(self) -> None:
        gateway = FakeGateway(default=records({"sys_id": "cat1"}))
        service = CatalogService(gateway, policy())

        service.categories()

        assert gateway.last().params == {"sysparm_limit": "100"}


class TestCodeDefaults:
    """The code service's default request."""

    def test_searching_asks_for_fifty_and_no_type_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, policy())

        service.search("foo")

        assert gateway.last().params == {
            "sysparm_query": "scriptLIKEfoo^ORnameLIKEfoo^ORdescriptionLIKEfoo",
            "sysparm_limit": "50",
        }

    def test_listing_artefacts_asks_for_fifty(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, policy())

        service.list("business_rule")

        assert gateway.last().params == {
            "sysparm_limit": "50",
            "sysparm_query": "type=business rule",
        }

    def test_where_used_asks_for_one_hundred_in_the_code(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, policy())

        service.where_used("foo")

        assert gateway.calls[0].params["sysparm_limit"] == "100"

    def test_where_used_asks_for_two_hundred_in_the_schema(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, policy())

        service.where_used("foo")

        assert gateway.calls[1].params["sysparm_limit"] == "200"


class TestOpsDefaults:
    """The operations service's default request."""

    def test_the_log_asks_for_fifty_with_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"message": "oops"}))
        service = OpsService(gateway, policy())

        service.log()

        call = gateway.last()
        assert call.path == "/api/now/table/sys_log"
        assert call.params == {"sysparm_limit": "50"}

    def test_jobs_ask_for_fifty(self) -> None:
        gateway = FakeGateway(default=records({"name": "Nightly"}))
        service = OpsService(gateway, policy())

        service.jobs()

        assert gateway.last().params == {"sysparm_limit": "50"}

    def test_properties_ask_for_two_hundred(self) -> None:
        gateway = FakeGateway(default=records({"name": "a", "value": "b"}))
        service = OpsService(gateway, policy())

        service.properties()

        assert gateway.last().params == {"sysparm_limit": "200"}


class TestAdminDefaults:
    """The administrative service's default request."""

    def test_update_sets_ask_for_fifty(self) -> None:
        gateway = FakeGateway(default=records({"name": "Sprint 1"}))
        service = AdminService(gateway, policy())

        service.update_sets()

        assert gateway.last().params == {"sysparm_limit": "50"}

    def test_users_ask_for_fifty_with_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"user_name": "a"}))
        service = AdminService(gateway, policy())

        service.users()

        assert gateway.last().params == {"sysparm_limit": "50"}

    def test_groups_ask_for_fifty_with_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "Support"}))
        service = AdminService(gateway, policy())

        service.groups()

        assert gateway.last().params == {"sysparm_limit": "50"}

    def test_roles_ask_for_fifty_with_no_filter(self) -> None:
        gateway = FakeGateway(default=records({"name": "admin"}))
        service = AdminService(gateway, policy())

        service.roles()

        assert gateway.last().params == {"sysparm_limit": "50"}


class TestGraphDefaults:
    """The graph service's default request."""

    def test_relations_ask_in_both_directions_for_two_hundred(self) -> None:
        gateway = FakeGateway(default=records({"parent": "p1", "child": "c1"}))
        service = GraphService(gateway, policy())

        service.relations("p1")

        call = gateway.last()
        assert call.path == "/api/now/table/cmdb_rel_ci"
        assert call.params == {"sysparm_query": "parent=p1^ORchild=p1", "sysparm_limit": "200"}

    def test_csdm_models_probe_for_the_table_first(self) -> None:
        gateway = FakeGateway(default=records({"name": "sys_csdm_domain_model"}))
        service = GraphService(gateway, policy())

        service.csdm_models()

        probe = gateway.calls[0]
        assert probe.path == "/api/now/table/sys_db_object"
        assert probe.params == {
            "sysparm_query": "name=sys_csdm_domain_model",
            "sysparm_limit": "1",
        }

    def test_csdm_models_ask_for_one_hundred(self) -> None:
        gateway = FakeGateway(default=records({"name": "sys_csdm_domain_model"}))
        service = GraphService(gateway, policy())

        service.csdm_models()

        assert gateway.calls[1].params == {"sysparm_limit": "100"}

    def test_csdm_context_probe_asks_for_the_table_first(self) -> None:
        gateway = FakeGateway(default=records({"name": "sys_csdm_context"}))
        service = GraphService(gateway, policy())

        service.csdm_context("Service Domain")

        probe = gateway.calls[0]
        assert probe.path == "/api/now/table/sys_db_object"
        assert probe.params == {
            "sysparm_query": "name=sys_csdm_context",
            "sysparm_limit": "1",
        }

    def test_csdm_context_asks_for_the_model_and_one_hundred(self) -> None:
        gateway = FakeGateway(default=records({"name": "sys_csdm_context"}))
        service = GraphService(gateway, policy())

        service.csdm_context("Service Domain")

        assert gateway.calls[1].params == {
            "sysparm_query": "domain_model=Service Domain",
            "sysparm_limit": "100",
        }


class TestAggregateDefaults:
    """The aggregate service's default request."""

    def test_counting_asks_for_the_count_aggregate_only(self) -> None:
        gateway = FakeGateway(default=records({"aggregate": 1}))
        service = AggregateService(gateway, policy())

        service.stats("incident", "COUNT")

        call = gateway.last()
        assert call.path == "/api/now/stats/incident"
        assert call.params == {"sysparm_aggregate": "COUNT"}


class TestCsdmHonesty:
    """CSDM tables are not in ServiceNow's public contract, and the server
    says so exactly rather than approximately."""

    def test_the_models_reason_is_exact(self) -> None:
        gateway = FakeGateway(
            responses={"/api/now/table/sys_db_object": ok({"result": []})}
        )
        service = GraphService(gateway, policy())

        result = service.csdm_models()

        assert result == {
            "available": False,
            "reason": (
                "the table 'sys_csdm_domain_model' is not present on this instance; "
                "it is not part of ServiceNow's public documented contract"
            ),
            "models": [],
        }

    def test_the_context_reason_is_exact(self) -> None:
        gateway = FakeGateway(
            responses={"/api/now/table/sys_db_object": ok({"result": []})}
        )
        service = GraphService(gateway, policy())

        result = service.csdm_context("Service Domain")

        assert result == {
            "available": False,
            "reason": (
                "the table 'sys_csdm_context' is not present on this instance; "
                "it is not part of ServiceNow's public documented contract"
            ),
            "contexts": [],
        }

    def test_the_available_models_answer_is_exact(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": records({"name": "sys_csdm_domain_model"}),
                "/api/now/table/sys_csdm_domain_model": records({"name": "Service Domain"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.csdm_models() == {
            "available": True,
            "models": [{"name": "Service Domain"}],
        }

    def test_the_available_contexts_answer_is_exact(self) -> None:
        gateway = FakeGateway(
            responses={
                "/api/now/table/sys_db_object": records({"name": "sys_csdm_context"}),
                "/api/now/table/sys_csdm_context": records({"name": "Service Domain"}),
            }
        )
        service = GraphService(gateway, policy())

        assert service.csdm_context("Service Domain") == {
            "available": True,
            "model": "Service Domain",
            "contexts": [{"name": "Service Domain"}],
        }

    def test_a_failed_probe_counts_as_absent(self) -> None:
        gateway = FakeGateway(
            responses={"/api/now/table/sys_db_object": records({"name": "sys_csdm_context"})}
        )
        service = GraphService(gateway, policy())

        assert service.csdm_context("Service Domain")["available"] is True
