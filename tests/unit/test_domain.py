"""Tier 1 - unit tests. The domain's own rules, in isolation.

Error messages are asserted exactly (anchored), not by substring: a message is
part of the contract, and loose matching lets a corrupted message ship.
"""

from __future__ import annotations

import pytest

from snowmcp.domain.errors import SafetyGuardError, ValidationError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import GraphNode, Query, Record, Relation, TableRef
from snowmcp.domain.storage import tags_from


def test_table_ref_accepts_a_valid_name() -> None:
    assert TableRef("incident").name == "incident"


def test_table_ref_rejects_a_name_with_a_path_separator() -> None:
    with pytest.raises(ValidationError, match=r"^invalid table name: 'incident/x'$"):
        TableRef("incident/x")


def test_table_ref_rejects_a_name_starting_with_a_digit() -> None:
    with pytest.raises(ValidationError, match=r"^invalid table name: '1table'$"):
        TableRef("1table")


def test_table_ref_rejects_an_empty_name() -> None:
    with pytest.raises(ValidationError, match=r"^invalid table name: ''$"):
        TableRef("")


def test_table_ref_builds_its_table_api_endpoint() -> None:
    assert TableRef("incident").endpoint == "/api/now/table/incident"


def test_query_defaults_are_sane() -> None:
    query = Query(table="incident")
    assert query.limit == 100
    assert query.offset == 0
    assert query.fields == ()


def test_query_rejects_a_limit_below_one() -> None:
    with pytest.raises(ValidationError, match=r"^limit must be at least 1$"):
        Query(table="incident", limit=0)


def test_query_rejects_a_limit_above_the_maximum() -> None:
    with pytest.raises(ValidationError, match=r"^limit must not exceed 10000$"):
        Query(table="incident", limit=10001)


def test_query_accepts_the_maximum_limit() -> None:
    assert Query(table="incident", limit=10000).limit == 10000


def test_query_rejects_a_negative_offset() -> None:
    with pytest.raises(ValidationError, match=r"^offset must not be negative$"):
        Query(table="incident", offset=-1)


def test_an_aggregate_may_be_grouped() -> None:
    """ServiceNow's Table API uses sysparm_aggregate with sysparm_group_by."""
    query = Query(table="incident", aggregate="COUNT", group_by="state")

    assert query.aggregate == "COUNT"
    assert query.group_by == "state"


def test_record_prefers_a_display_value_over_the_raw_field() -> None:
    record = Record(
        sys_id="abc",
        table="incident",
        fields={"state": "2"},
        display_values={"state": "In Progress"},
    )
    assert record.get("state") == "In Progress"


def test_record_falls_back_to_the_raw_field() -> None:
    record = Record(sys_id="abc", table="incident", fields={"state": "2"})
    assert record.get("state") == "2"


def test_record_returns_the_default_for_an_unknown_field() -> None:
    record = Record(sys_id="abc", table="incident")
    assert record.get("nope", "fallback") == "fallback"


def test_record_from_payload_separates_display_values() -> None:
    record = Record.from_payload(
        {"sys_id": "abc", "number": "INC01", "display_value:number": "INC0001"},
        table="incident",
    )
    assert record.sys_id == "abc"
    assert record.fields["number"] == "INC01"
    assert record.display_values == {"number": "INC0001"}
    assert record.get("number") == "INC0001"


def test_record_from_payload_keeps_only_the_core_sys_fields() -> None:
    record = Record.from_payload(
        {"sys_id": "abc", "sys_created_on": "2026-01-01", "sys_updated_on": "2026-01-02"},
        table="incident",
    )
    assert "sys_created_on" in record.fields
    assert "sys_updated_on" in record.fields


def test_relation_and_graph_node_are_value_objects() -> None:
    relation = Relation(parent_sys_id="a", child_sys_id="b", type_sys_id="t")
    node = GraphNode(sys_id="b", table="server", depth=1)
    assert relation.parent_sys_id == "a"
    assert node.depth == 1


def test_tags_from_normalises_a_comma_separated_string() -> None:
    assert tags_from("alpha, beta ,alpha") == ("alpha", "beta")


def test_tags_from_accepts_a_sequence() -> None:
    assert tags_from(["alpha", " beta "]) == ("alpha", "beta")


def test_tags_from_none_is_empty() -> None:
    assert tags_from(None) == ()


class TestWritePolicy:
    """The safety controls."""

    def test_a_write_without_confirmation_is_refused(self) -> None:
        policy = WritePolicy(require_confirm=True)
        with pytest.raises(
            SafetyGuardError, match=r"^write to 'incident' needs confirmation: pass confirm=true$"
        ):
            policy.check_write("incident")

    def test_a_confirmed_write_is_allowed(self) -> None:
        policy = WritePolicy(require_confirm=True)
        policy.check_write("incident", confirmed=True)

    def test_read_only_mode_refuses_every_write(self) -> None:
        policy = WritePolicy(read_only=True, require_confirm=False)
        with pytest.raises(SafetyGuardError, match=r"^server is in read-only mode$"):
            policy.check_write("incident", confirmed=True)

    def test_a_denied_table_is_refused(self) -> None:
        policy = WritePolicy(denied_tables=frozenset({"sys_user"}), require_confirm=False)
        with pytest.raises(SafetyGuardError, match=r"^table 'sys_user' is denied by policy$"):
            policy.check_read("sys_user")

    def test_a_table_outside_the_allow_list_is_refused(self) -> None:
        policy = WritePolicy(allowed_tables=frozenset({"incident"}), require_confirm=False)
        with pytest.raises(
            SafetyGuardError, match=r"^table 'change_request' is not in the allow list$"
        ):
            policy.check_read("change_request")

    def test_an_allow_list_permits_its_own_tables(self) -> None:
        policy = WritePolicy(allowed_tables=frozenset({"incident"}), require_confirm=False)
        policy.check_read("incident")

    def test_a_batch_over_the_limit_is_refused(self) -> None:
        policy = WritePolicy(max_batch=2, require_confirm=False)
        with pytest.raises(SafetyGuardError, match=r"^batch of 3 exceeds the limit of 2$"):
            policy.check_batch(3)

    def test_a_batch_within_the_limit_is_allowed(self) -> None:
        policy = WritePolicy(max_batch=2, require_confirm=False)
        policy.check_batch(2)
