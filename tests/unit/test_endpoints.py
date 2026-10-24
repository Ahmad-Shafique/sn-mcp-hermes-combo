"""Tier 1 - unit tests for the endpoint and parameter policy.

These functions decide exactly what the server asks the instance for, so they
are worth pinning down precisely.
"""

from __future__ import annotations

import pytest

from snowmcp.application import endpoints
from snowmcp.domain.errors import ValidationError
from snowmcp.domain.records import Query


def test_the_table_path_is_built() -> None:
    assert endpoints.table_path("incident") == "/api/now/table/incident"


def test_the_record_path_is_built() -> None:
    assert endpoints.record_path("incident", "abc") == "/api/now/table/incident/abc"


def test_the_stats_path_is_built() -> None:
    assert endpoints.stats_path("incident") == "/api/now/stats/incident"


def test_the_aggregate_api_path_is_built() -> None:
    assert endpoints.aggregate_api_path("incident") == "/api/now/aggregate/incident"


def test_the_cmdb_paths_are_built() -> None:
    assert endpoints.cmdb_path() == "/api/now/cmdb"
    assert endpoints.cmdb_ci_path("abc") == "/api/now/cmdb/ci/abc"


def test_the_attachment_path_is_built() -> None:
    assert endpoints.attachment_path("att1") == "/api/now/attachment/att1"


def test_the_script_path_is_the_table_path() -> None:
    assert endpoints.script_path("sys_script") == "/api/now/table/sys_script"


def test_an_invalid_table_name_is_refused() -> None:
    with pytest.raises(ValidationError, match=r"^invalid table name"):
        endpoints.table_path("incident/../sys_user")


def test_query_params_carry_only_what_was_set() -> None:
    params = endpoints.query_params(Query(table="incident"))

    assert params == {"sysparm_limit": "100"}


def test_query_params_carry_the_full_filter() -> None:
    params = endpoints.query_params(
        Query(
            table="incident",
            encoded_query="state=2",
            fields=("number", "state"),
            limit=10,
            offset=20,
            order_by="number",
            display_value=True,
        )
    )

    assert params["sysparm_query"] == "state=2"
    assert params["sysparm_fields"] == "number,state"
    assert params["sysparm_limit"] == "10"
    assert params["sysparm_offset"] == "20"
    assert params["sysparm_order_by"] == "number"
    assert params["sysparm_display_value"] == "true"


def test_query_params_carry_an_aggregate_and_a_group() -> None:
    params = endpoints.query_params(Query(table="incident", aggregate="COUNT", group_by="state"))

    assert params["sysparm_aggregate"] == "COUNT"
    assert params["sysparm_group_by"] == "state"


def test_stats_params_carry_the_aggregate() -> None:
    params = endpoints.stats_params("COUNT")

    assert params == {"sysparm_aggregate": "COUNT"}


def test_stats_params_carry_the_filters() -> None:
    params = endpoints.stats_params("SUM", encoded_query="state=2", group_by="a", group_by_2="b")

    assert params["sysparm_query"] == "state=2"
    assert params["sysparm_group_by"] == "a"
    assert params["sysparm_group_by_2"] == "b"


def test_the_relations_query_covers_both_directions() -> None:
    params = endpoints.cmdb_relations_params("abc")

    assert params["sysparm_query"] == "parent=abc^ORchild=abc"


def test_the_relations_query_can_go_down_only() -> None:
    assert endpoints.cmdb_relations_params("abc", direction="down")["sysparm_query"] == "parent=abc"


def test_the_relations_query_can_go_up_only() -> None:
    assert endpoints.cmdb_relations_params("abc", direction="up")["sysparm_query"] == "child=abc"


def test_the_relations_limit_scales_with_depth() -> None:
    assert endpoints.cmdb_relations_params("abc", depth=3)["sysparm_limit"] == "300"


def test_where_used_params_find_both_reference_forms() -> None:
    params = endpoints.where_used_params("short_description")

    assert "element_reference_name=short_description" in params["sysparm_query"]
    assert "name=short_description" in params["sysparm_query"]


def test_the_script_search_covers_script_name_and_description() -> None:
    params = endpoints.script_search_params("Needle")

    assert "scriptLIKENeedle" in params["sysparm_query"]
    assert "nameLIKENeedle" in params["sysparm_query"]
    assert "descriptionLIKENeedle" in params["sysparm_query"]


def test_the_script_search_can_filter_by_type() -> None:
    params = endpoints.script_search_params("Needle", script_type="business rule")

    assert "type=business rule" in params["sysparm_query"]


def test_the_batch_body_carries_the_operations() -> None:
    body = endpoints.batch_body([{"method": "POST"}])

    assert body["operations"] == [{"method": "POST"}]
    assert body["batch_request_id"] is None


def test_the_table_list_params_can_filter_by_pattern() -> None:
    params = endpoints.table_list_params("inc")

    assert params["sysparm_query"] == "nameLIKEinc"


def test_the_table_list_params_without_a_pattern_list_everything() -> None:
    params = endpoints.table_list_params("")

    assert "sysparm_query" not in params
    assert params["sysparm_limit"] == "200"


def test_the_artefact_table_map_covers_the_usual_artefacts() -> None:
    assert endpoints.CODE_TABLES["business_rule"] == "sys_script"
    assert endpoints.CODE_TABLES["ui_policy"] == "sys_ui_policy"
    assert endpoints.CODE_TABLES["acl"] == "sys_security_acl"


def test_the_script_type_map_covers_the_usual_artefacts() -> None:
    assert endpoints.SCRIPT_TYPE_BY_ARTEFACT["business_rule"] == "business rule"
    assert endpoints.SCRIPT_TYPE_BY_ARTEFACT["script_include"] == "script include"
