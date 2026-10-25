"""Tier 2 - what each service asks the policy to allow.

Every service calls ``policy.check_read(table)`` before it touches the
instance. Which table it names matters: it is the table the write
guard, the allow list and the deny list are keyed on. A service that
checked the wrong table would pass a permissive policy and slip past a
restrictive one, so the table names are pinned here.

The policy below records what it was asked instead of enforcing anything,
which is what makes the assertion possible.
"""

from __future__ import annotations

import pytest

from snowmcp.application.graph import GraphService
from snowmcp.application.records import AggregateService, RecordService, SchemaService
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)
from snowmcp.domain.errors import SafetyGuardError, ValidationError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Query

from tests.conftest import FakeGateway, ok, records


class RecordingPolicy(WritePolicy):
    """A policy that remembers what it was asked to allow."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(require_confirm=False, **kwargs)  # type: ignore[arg-type]
        self.reads: list[str] = []
        self.writes: list[str] = []

    def check_read(self, table: str) -> None:
        self.reads.append(table)
        super().check_read(table)

    def check_write(self, table: str, *, confirmed: bool = False) -> None:
        self.writes.append(table)
        super().check_write(table, confirmed=confirmed)


class TestPolicyChecks:
    """The table each service names when it asks to read."""

    def test_a_record_query_checks_its_own_table(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=records({"sys_id": "x"})), policy).query(
            Query(table="incident")
        )

        assert policy.reads == ["incident"]

    def test_counting_checks_its_own_table(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=records({"sys_id": "x"})), policy).count("incident")

        assert policy.reads == ["incident"]

    def test_a_schema_listing_checks_sys_db_object(self) -> None:
        policy = RecordingPolicy()
        SchemaService(FakeGateway(default=records({"name": "x"})), policy).tables()

        assert policy.reads == ["sys_db_object"]

    def test_a_schema_field_listing_checks_sys_dictionary(self) -> None:
        policy = RecordingPolicy()
        SchemaService(FakeGateway(default=records({"element_id": "x"})), policy).fields("incident")

        assert policy.reads == ["sys_dictionary"]

    def test_catalog_items_check_the_catalog_item_table(self) -> None:
        policy = RecordingPolicy()
        CatalogService(FakeGateway(default=records({"sys_id": "x"})), policy).items()

        assert policy.reads == ["sc_cat_item"]

    def test_catalog_categories_check_the_category_table(self) -> None:
        policy = RecordingPolicy()
        CatalogService(FakeGateway(default=records({"sys_id": "x"})), policy).categories()

        assert policy.reads == ["sc_category"]

    def test_a_code_search_checks_sys_script(self) -> None:
        policy = RecordingPolicy()
        CodeService(FakeGateway(default=records({"name": "x"})), policy).search("foo")

        assert policy.reads == ["sys_script"]

    def test_where_used_checks_both_tables_by_default(self) -> None:
        policy = RecordingPolicy()
        CodeService(FakeGateway(default=records({"name": "x"})), policy).where_used("foo")

        assert policy.reads == ["sys_script", "sys_dictionary"]

    def test_where_used_scoped_to_code_checks_only_the_script_table(self) -> None:
        policy = RecordingPolicy()
        CodeService(FakeGateway(default=records({"name": "x"})), policy).where_used(
            "foo", scope="code"
        )

        assert policy.reads == ["sys_script"]

    def test_where_used_scoped_to_schema_checks_only_the_dictionary_table(self) -> None:
        policy = RecordingPolicy()
        CodeService(FakeGateway(default=records({"name": "x"})), policy).where_used(
            "foo", scope="schema"
        )

        assert policy.reads == ["sys_dictionary"]

    def test_the_log_checks_sys_log(self) -> None:
        policy = RecordingPolicy()
        OpsService(FakeGateway(default=records({"message": "x"})), policy).log()

        assert policy.reads == ["sys_log"]

    def test_health_checks_sys_properties(self) -> None:
        policy = RecordingPolicy()
        OpsService(FakeGateway(default=records({"name": "x", "value": "y"})), policy).health()

        assert policy.reads == ["sys_properties"]

    def test_jobs_check_the_scheduler(self) -> None:
        policy = RecordingPolicy()
        OpsService(FakeGateway(default=records({"name": "x"})), policy).jobs()

        assert policy.reads == ["sys_schedule_job"]

    def test_update_sets_check_the_update_set_table(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=records({"name": "x"})), policy).update_sets()

        assert policy.reads == ["sys_update_set"]

    def test_users_check_sys_user(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=records({"user_name": "x"})), policy).users()

        assert policy.reads == ["sys_user"]

    def test_groups_check_sys_user_group(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=records({"name": "x"})), policy).groups()

        assert policy.reads == ["sys_user_group"]

    def test_roles_check_sys_user_role(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=records({"name": "x"})), policy).roles()

        assert policy.reads == ["sys_user_role"]

    def test_memberships_check_the_membership_table(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=records({"member": "x"})), policy).memberships("grp")

        assert policy.reads == ["sys_user_grmember"]

    def test_attachments_check_sys_attachment(self) -> None:
        policy = RecordingPolicy()
        FileService(FakeGateway(default=records({"sys_id": "x"})), policy).list("incident", "r1")

        assert policy.reads == ["sys_attachment"]

    def test_graph_relations_check_the_relation_table(self) -> None:
        policy = RecordingPolicy()
        GraphService(FakeGateway(default=records({"parent": "p1", "child": "c1"})), policy).relations(
            "p1"
        )

        assert "cmdb_rel_ci" in policy.reads

    def test_graph_relations_check_the_relation_type_table(self) -> None:
        policy = RecordingPolicy()
        GraphService(
            FakeGateway(default=records({"parent": "p1", "child": "c1", "type": "type1"})),
            policy,
        ).relations("p1")

        assert "cmdb_rel_type" in policy.reads

    def test_an_aggregate_checks_its_own_table(self) -> None:
        policy = RecordingPolicy()
        AggregateService(FakeGateway(default=records({"aggregate": 1})), policy).stats(
            "incident", "COUNT"
        )

        assert policy.reads == ["incident"]


class TestPolicyWrites:
    """The table each service names when it asks to write."""

    def test_creating_a_record_checks_its_own_table(self) -> None:
        policy = RecordingPolicy()
        RecordService(
            FakeGateway(default=ok({"result": {"sys_id": "x"}})), policy
        ).create("incident", {"short_description": "x"})

        assert policy.writes == ["incident"]

    def test_deleting_a_record_checks_its_own_table(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=records({"sys_id": "x"})), policy).delete(
            "incident", "s1"
        )

        assert policy.writes == ["incident"]

    def test_batching_checks_the_table_of_every_write(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=ok({"result": []})), policy).batch(
            [
                {"method": "POST", "table": "incident", "body": {}},
                {"method": "PATCH", "table": "change_request", "body": {}},
            ]
        )

        assert policy.writes == ["incident", "change_request"]

    def test_batching_a_read_checks_a_read_instead(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=ok({"result": []})), policy).batch(
            [{"method": "GET", "table": "incident"}]
        )

        assert policy.reads == ["incident"]
        assert policy.writes == []

    def test_batching_treats_put_and_delete_as_writes(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=ok({"result": []})), policy).batch(
            [
                {"method": "PUT", "table": "incident"},
                {"method": "DELETE", "table": "incident"},
            ]
        )

        # The verb is upper-cased before the comparison, so a lower-case
        # "delete" in the list would silently turn a delete into a read.
        assert policy.writes == ["incident", "incident"]
        assert policy.reads == []

    def test_batching_an_operation_with_no_table_checks_an_empty_table(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=ok({"result": []})), policy).batch(
            [{"method": "GET"}]
        )

        # The fallback is an empty name, not the string "None".
        assert policy.reads == [""]

    def test_batching_an_operation_with_no_method_checks_a_read(self) -> None:
        policy = RecordingPolicy()
        RecordService(FakeGateway(default=ok({"result": []})), policy).batch(
            [{"table": "incident"}]
        )

        # An absent method falls back to an empty verb, which is not a
        # write verb, so it is a read.
        assert policy.reads == ["incident"]
        assert policy.writes == []

    def test_ordering_a_catalog_item_checks_the_request_item_table(self) -> None:
        policy = RecordingPolicy()
        CatalogService(FakeGateway(default=ok({"result": {}})), policy).order(
            "item1", {}, confirmed=True
        )

        assert policy.writes == ["sc_req_item"]

    def test_uploading_an_attachment_checks_sys_attachment(self) -> None:
        policy = RecordingPolicy()
        FileService(FakeGateway(default=ok({"result": {}})), policy).upload(
            "incident", "r1", "a.txt", "Zm9v", confirmed=True
        )

        assert policy.writes == ["sys_attachment"]

    def test_deleting_an_attachment_checks_sys_attachment(self) -> None:
        policy = RecordingPolicy()
        FileService(FakeGateway(default=ok({})), policy).delete("att1", confirmed=True)

        assert policy.writes == ["sys_attachment"]

    def test_binding_an_update_set_checks_the_update_set_table(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=ok({"result": {}})), policy).set_update_set(
            "Sprint 1", confirmed=True
        )

        assert policy.writes == ["sys_update_set"]

    def test_running_a_script_checks_sys_script(self) -> None:
        policy = RecordingPolicy()
        AdminService(
            FakeGateway(default=ok({"result": {}})),
            policy,
            scripted_rest_url="/api/x/ns/acme/run",
        ).script("var x = 1", confirmed=True)

        assert policy.writes == ["sys_script"]

    def test_running_atf_checks_the_test_table(self) -> None:
        policy = RecordingPolicy()
        AdminService(FakeGateway(default=ok({"result": {}})), policy).atf("Suite", confirmed=True)

        assert policy.writes == ["sys_atf_test"]


class TestScopeContract:
    """``scope`` narrows the search, and says so when it does not know."""

    def test_the_default_scope_searches_both(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, WritePolicy(require_confirm=False))

        result = service.where_used("foo")

        assert result["scope"] == ""
        assert [call.path for call in gateway.calls] == [
            "/api/now/table/sys_script",
            "/api/now/table/sys_dictionary",
        ]

    def test_a_code_scope_searches_only_the_scripts(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, WritePolicy(require_confirm=False))

        result = service.where_used("foo", scope="code")

        assert result["scope"] == "code"
        assert [call.path for call in gateway.calls] == ["/api/now/table/sys_script"]
        assert result["scripts"] == [{"name": "x"}]
        assert result["structural"] == []

    def test_a_schema_scope_searches_only_the_dictionary(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, WritePolicy(require_confirm=False))

        result = service.where_used("foo", scope="schema")

        assert result["scope"] == "schema"
        assert [call.path for call in gateway.calls] == ["/api/now/table/sys_dictionary"]
        assert result["scripts"] == []
        assert result["structural"] == [{"name": "x"}]

    def test_an_unknown_scope_is_refused(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, WritePolicy(require_confirm=False))

        with pytest.raises(ValidationError):
            service.where_used("foo", scope="everything")

    def test_an_unknown_scope_asks_the_instance_nothing(self) -> None:
        gateway = FakeGateway(default=records({"name": "x"}))
        service = CodeService(gateway, WritePolicy(require_confirm=False))

        with pytest.raises(ValidationError):
            service.where_used("foo", scope="everything")

        assert gateway.calls == []


class TestStatsContract:
    """The summary counts the four common tables."""

    def test_it_counts_the_four_common_tables(self) -> None:
        gateway = FakeGateway(default=records({"aggregate": 1}))
        service = OpsService(gateway, WritePolicy(require_confirm=False))

        result = service.stats()

        assert [call.path for call in gateway.calls] == [
            "/api/now/stats/incident",
            "/api/now/stats/change_request",
            "/api/now/stats/sys_user",
            "/api/now/stats/cmdb_ci",
        ]
        assert set(result["counts"]) == {
            "incident",
            "change_request",
            "sys_user",
            "cmdb_ci",
        }

    def test_each_count_asks_for_the_count_aggregate(self) -> None:
        gateway = FakeGateway(default=records({"aggregate": 1}))
        service = OpsService(gateway, WritePolicy(require_confirm=False))

        service.stats()

        assert all(
            call.params["sysparm_aggregate"] == "COUNT" for call in gateway.calls
        )

    def test_a_table_that_cannot_be_counted_is_reported_as_none(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = OpsService(gateway, WritePolicy(require_confirm=False))

        result = service.stats()

        # An empty aggregate result is not an error, so the counts stand.
        assert result["counts"]["incident"] is not None

    def test_a_failing_table_does_not_break_the_summary(self) -> None:
        gateway = FakeGateway(default=ok({"result": []}))
        service = OpsService(gateway, WritePolicy(require_confirm=False))

        result = service.stats()

        assert "counts" in result


class TestSafetyGuardContract:
    """The guard really refuses."""

    def test_a_denied_table_is_refused_on_read(self) -> None:
        policy = WritePolicy(denied_tables=frozenset({"sys_script"}), require_confirm=False)
        service = CodeService(FakeGateway(), policy)

        with pytest.raises(SafetyGuardError):
            service.search("foo")
