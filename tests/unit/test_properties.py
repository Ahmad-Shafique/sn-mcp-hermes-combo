"""Tier 1 - property-based tests.

"Example tests say what should happen; properties say what must not."

An example test pins one input and one output. A property test states an
invariant and then throws thousands of generated inputs at it, looking for
the one that breaks it. That is the difference between a suite that passed
today and a suite that would have caught the bug you haven't met yet.

Every property below is an invariant the code claims to hold *for all
inputs*, not an example of it holding for one.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from snowmcp.application import endpoints
from snowmcp.domain.errors import SafetyGuardError, ValidationError
from snowmcp.domain.policy import WritePolicy
from snowmcp.domain.records import Query, Record, RecordPage, TableRef
from snowmcp.domain.storage import (
    CachedRecord,
    CallRecord,
    JournalEntry,
    Note,
    SavedQuery,
    tags_from,
)

VALID_TABLE = st.from_regex(r"\A[A-Za-z][A-Za-z0-9_]*\Z", fullmatch=True)


class TestTableRefProperties:
    """A table name is either wholly valid or wholly refused."""

    @given(name=VALID_TABLE)
    def test_a_well_formed_name_is_accepted(self, name: str) -> None:
        assert TableRef(name).name == name

    @given(name=VALID_TABLE)
    def test_the_endpoint_always_contains_the_name(self, name: str) -> None:
        assert TableRef(name).endpoint == f"/api/now/table/{name}"

    @given(name=st.text(min_size=1, max_size=30).filter(lambda s: not s[0].isalpha()))
    def test_a_name_that_does_not_start_with_a_letter_is_refused(self, name: str) -> None:
        try:
            TableRef(name)
        except ValidationError:
            return
        raise AssertionError(f"{name!r} should have been refused")

    @given(
        name=st.builds(
            lambda prefix, escape: prefix + escape,
            st.text(alphabet="abcXYZ", min_size=1, max_size=5),
            st.sampled_from(["/", "..", "/..", "../", "//"]),
        )
    )
    def test_a_name_that_could_escape_its_path_segment_is_refused(self, name: str) -> None:
        try:
            TableRef(name)
        except ValidationError:
            return
        raise AssertionError(f"{name!r} should have been refused")


class TestQueryProperties:
    """A query never carries an impossible page or a smuggled table."""

    @given(table=VALID_TABLE, limit=st.integers(min_value=1, max_value=10000))
    def test_a_valid_table_and_limit_are_always_accepted(self, table: str, limit: int) -> None:
        assert Query(table=table, limit=limit).limit == limit

    @given(limit=st.integers(min_value=10001, max_value=10**6))
    def test_a_limit_above_the_maximum_is_always_refused(self, limit: int) -> None:
        try:
            Query(table="incident", limit=limit)
        except ValidationError:
            return
        raise AssertionError(f"limit {limit} should have been refused")

    @given(limit=st.integers(min_value=-10**6, max_value=0))
    def test_a_limit_below_one_is_always_refused(self, limit: int) -> None:
        try:
            Query(table="incident", limit=limit)
        except ValidationError:
            return
        raise AssertionError(f"limit {limit} should have been refused")

    @given(offset=st.integers(min_value=-10**6, max_value=-1))
    def test_a_negative_offset_is_always_refused(self, offset: int) -> None:
        try:
            Query(table="incident", offset=offset)
        except ValidationError:
            return
        raise AssertionError(f"offset {offset} should have been refused")


class TestRecordProperties:
    """A record built from a payload keeps its identity and its precedence."""

    @given(sys_id=st.text(min_size=1, max_size=32))
    def test_the_sys_id_survives_the_round_trip(self, sys_id: str) -> None:
        record = Record.from_payload({"sys_id": sys_id, "number": "INC01"}, table="incident")
        assert record.sys_id == sys_id

    @given(value=st.text(max_size=20))
    def test_a_display_value_always_wins_over_the_raw_field(self, value: str) -> None:
        record = Record(
            sys_id="a",
            table="incident",
            fields={"state": "2"},
            display_values={"state": value},
        )
        assert record.get("state") == value

    @given(key=st.text(min_size=1, max_size=20))
    def test_an_unknown_field_always_returns_the_default(self, key: str) -> None:
        record = Record(sys_id="a", table="incident")
        assert record.get(key, "fallback") == "fallback"

    @given(count=st.integers(min_value=0, max_value=50))
    def test_a_page_knows_how_many_records_it_holds(self, count: int) -> None:
        records = tuple(Record(sys_id=str(index), table="incident") for index in range(count))
        assert len(RecordPage(records=records)) == count


class TestPolicyProperties:
    """Read-only really means read-only, whatever the table."""

    @given(table=VALID_TABLE)
    def test_read_only_mode_always_refuses_a_write(self, table: str) -> None:
        policy = WritePolicy(read_only=True, require_confirm=False)
        try:
            policy.check_write(table, confirmed=True)
        except SafetyGuardError as exc:
            assert "read-only" in str(exc)
            return
        raise AssertionError(f"a write to {table!r} should have been refused")

    @given(table=VALID_TABLE)
    def test_a_denied_table_is_always_refused(self, table: str) -> None:
        policy = WritePolicy(denied_tables=frozenset({table}), require_confirm=False)
        try:
            policy.check_read(table)
        except SafetyGuardError as exc:
            assert "denied by policy" in str(exc)
            return
        raise AssertionError(f"{table!r} should have been denied")

    @given(table=st.just("change_request"))
    def test_a_table_outside_the_allow_list_is_always_refused(self, table: str) -> None:
        policy = WritePolicy(allowed_tables=frozenset({"incident"}), require_confirm=False)
        try:
            policy.check_read(table)
        except SafetyGuardError:
            return
        raise AssertionError(f"{table!r} should not be in the allow list")

    @given(size=st.integers(min_value=1, max_value=100))
    def test_a_batch_at_or_below_the_limit_is_allowed(self, size: int) -> None:
        policy = WritePolicy(max_batch=100, require_confirm=False)
        policy.check_batch(size)

    @given(size=st.integers(min_value=101, max_value=10**6))
    def test_a_batch_above_the_limit_is_always_refused(self, size: int) -> None:
        policy = WritePolicy(max_batch=100, require_confirm=False)
        try:
            policy.check_batch(size)
        except SafetyGuardError:
            return
        raise AssertionError(f"a batch of {size} should have been refused")


class TestPayloadProperties:
    """Every stored payload always carries its identifying keys."""

    @given(key=st.text(min_size=1, max_size=40), title=st.text(max_size=40))
    def test_a_note_payload_always_carries_its_key_and_title(self, key: str, title: str) -> None:
        payload = Note(key=key, title=title, body="b").to_dict()
        assert payload["key"] == key
        assert payload["title"] == title

    @given(table=VALID_TABLE, sys_id=st.text(min_size=1, max_size=32))
    def test_a_cached_record_payload_always_names_its_table_and_record(
        self, table: str, sys_id: str
    ) -> None:
        payload = CachedRecord(table=table, sys_id=sys_id, payload={}).to_dict()
        assert payload["table"] == table
        assert payload["sys_id"] == sys_id

    @given(name=st.text(min_size=1, max_size=40), table=VALID_TABLE)
    def test_a_saved_query_payload_always_names_its_table(self, name: str, table: str) -> None:
        payload = SavedQuery(name=name, table=table).to_dict()
        assert payload["name"] == name
        assert payload["table"] == table

    @given(tool=st.text(min_size=1, max_size=30), summary=st.text(max_size=80))
    def test_a_call_record_payload_always_carries_its_tool(self, tool: str, summary: str) -> None:
        payload = CallRecord(tool=tool, summary=summary).to_dict()
        assert payload["tool"] == tool

    @given(entry_id=st.text(min_size=1, max_size=60))
    def test_a_journal_entry_payload_always_carries_its_id(self, entry_id: str) -> None:
        entry = JournalEntry(entry_id=entry_id, operation="create", table="incident", sys_id="a")
        assert entry.to_dict()["entry_id"] == entry_id


class TestTagProperties:
    """Tags are clean, unique and keep their order."""

    @given(tags=st.lists(st.text(max_size=12), max_size=10))
    def test_tags_never_contain_a_blank(self, tags: list[str]) -> None:
        assert all(tag.strip() for tag in tags_from(tags))

    @given(tags=st.lists(st.text(max_size=12), max_size=10))
    def test_tags_are_unique(self, tags: list[str]) -> None:
        result = tags_from(tags)
        assert len(result) == len(set(result))


class TestEndpointProperties:
    """A path built from a table name can never escape its own segment."""

    @given(table=VALID_TABLE)
    def test_a_table_path_always_has_exactly_one_segment_after_the_api_root(
        self, table: str
    ) -> None:
        path = endpoints.table_path(table)
        assert path.startswith("/api/now/table/")
        assert "/" not in path[len("/api/now/table/") :]

    @given(table=VALID_TABLE, limit=st.integers(min_value=1, max_value=10000))
    def test_query_params_always_carry_a_limit(self, table: str, limit: int) -> None:
        params = endpoints.query_params(Query(table=table, limit=limit))
        assert params["sysparm_limit"] == str(limit)

    @given(table=VALID_TABLE)
    def test_query_params_never_carry_an_empty_query(self, table: str) -> None:
        params = endpoints.query_params(Query(table=table))
        assert params.get("sysparm_query", "x") != ""
