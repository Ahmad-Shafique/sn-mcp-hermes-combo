"""Tier 1 - unit tests that close the last behavioural branches.

Each test pins one specific edge: a timeout, an empty filter, a value of an
unexpected shape.
"""

from __future__ import annotations

import pytest

from snowmcp.application.ports import Response
from snowmcp.application.responses import unwrap_list
from snowmcp.application.services import AdminService, CodeService
from snowmcp.domain.errors import ServiceNowAPIError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import GraphNode, Record, RecordPage, Relation

from tests.conftest import FakeGateway, ok, records


def policy() -> WritePolicy:
    """A permissive policy."""
    return WritePolicy(require_confirm=False)


def test_a_record_page_knows_its_length() -> None:
    page = RecordPage(records=(Record(sys_id="a", table="incident"),))

    assert len(page) == 1


def test_an_empty_record_page_has_no_length() -> None:
    assert len(RecordPage(records=())) == 0


def test_a_relation_converts_to_a_plain_mapping() -> None:
    relation = Relation(
        parent_sys_id="p", child_sys_id="c", type_sys_id="t", parent_table="server"
    )

    assert relation.to_dict() == {
        "parent_sys_id": "p",
        "child_sys_id": "c",
        "type_sys_id": "t",
        "type_label": "",
        "parent_table": "server",
        "child_table": "",
    }


def test_a_graph_node_converts_to_a_plain_mapping() -> None:
    node = GraphNode(sys_id="c", table="server", name="web-01", depth=2)

    assert node.to_dict() == {
        "sys_id": "c",
        "table": "server",
        "name": "web-01",
        "depth": 2,
    }


def test_a_record_converts_to_a_plain_mapping() -> None:
    record = Record(sys_id="a", table="incident", fields={"n": 1}, display_values={"n": "one"})

    assert record.to_dict() == {
        "sys_id": "a",
        "table": "incident",
        "fields": {"n": 1},
        "display_values": {"n": "one"},
    }


def test_a_list_that_is_not_an_object_or_array_is_refused() -> None:
    with pytest.raises(ServiceNowAPIError, match=r"^expected a JSON array from the API$"):
        unwrap_list(Response(status=200, body="a string"))


def test_listing_a_script_artefact_filters_on_its_type() -> None:
    gateway = FakeGateway(default=records({"name": "Rule"}))
    service = CodeService(gateway, policy())

    service.list("business_rule")

    assert gateway.last().params["sysparm_query"] == "type=business rule"


def test_users_can_be_listed_without_a_filter() -> None:
    gateway = FakeGateway(default=records({"user_name": "a"}))
    service = AdminService(gateway, policy())

    service.users()

    assert "sysparm_query" not in gateway.last().params


def test_groups_can_be_filtered_by_text() -> None:
    gateway = FakeGateway(default=records({"name": "Support"}))
    service = AdminService(gateway, policy())

    service.groups(text="Sup")

    assert gateway.last().params["sysparm_query"] == "nameLIKESup^ORsys_idLIKESup"


def test_roles_can_be_listed_without_a_filter() -> None:
    gateway = FakeGateway(default=records({"name": "admin"}))
    service = AdminService(gateway, policy())

    service.roles()

    assert "sysparm_query" not in gateway.last().params


def test_a_timeout_is_reported_as_a_service_now_error(monkeypatch) -> None:
    import urllib.request

    from snowmcp.adapters.http.client import ServiceNowClient

    def fake_urlopen(request, timeout=None):
        raise TimeoutError()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    with pytest.raises(ServiceNowAPIError, match=r"^request to https://example.service-now.com/api/now/table/incident timed out after 60s$"):
        client.request("GET", "/api/now/table/incident")


def test_extra_headers_are_sent(monkeypatch) -> None:
    import urllib.request

    from snowmcp.adapters.http.client import ServiceNowClient

    seen: dict[str, object] = {}

    class FakeResponse:
        status = 200
        headers = {}

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def fake_urlopen(request, timeout=None):
        seen["headers"] = dict(request.headers)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = ServiceNowClient("https://example.service-now.com", username="u", password="p")

    client.request("GET", "/api/now/table/incident", headers={"X-Extra": "yes"})

    assert seen["headers"].get("X-extra") == "yes"
