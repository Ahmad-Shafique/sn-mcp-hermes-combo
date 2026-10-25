"""Domain records, queries and graph value objects.

These are the nouns the whole server speaks. They validate themselves, so no
layer above has to re-check them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from snowmcp.domain.errors import ValidationError

# ServiceNow table names: letter first, then letters, digits and underscores.
_TABLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

MAX_LIMIT = 10000
DEFAULT_LIMIT = 100


@dataclass(frozen=True)
class TableRef:
    """A ServiceNow table, validated so it can never escape its URL segment."""

    name: str

    def __post_init__(self) -> None:
        if not _TABLE_NAME.match(self.name):
            raise ValidationError(f"invalid table name: {self.name!r}")

    @property
    def endpoint(self) -> str:
        """The Table API path for this table."""
        return f"/api/now/table/{self.name}"


@dataclass(frozen=True)
class Query:
    """A Table API query: which table, which filter, which fields, which page."""

    table: str
    encoded_query: str = ""
    fields: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    order_by: str = ""
    display_value: bool = False
    aggregate: str = ""
    group_by: str = ""

    def __post_init__(self) -> None:
        TableRef(self.table)
        if self.limit < 1:
            raise ValidationError("limit must be at least 1")
        if self.limit > MAX_LIMIT:
            raise ValidationError(f"limit must not exceed {MAX_LIMIT}")
        if self.offset < 0:
            raise ValidationError("offset must not be negative")


@dataclass(frozen=True)
class Record:
    """One ServiceNow record."""

    sys_id: str
    table: str
    fields: Mapping[str, Any] = field(default_factory=dict)
    display_values: Mapping[str, str] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        """Read a field, preferring its display value when one was fetched."""
        if name in self.display_values:
            return self.display_values[name]
        return self.fields.get(name, default)

    def to_dict(self) -> dict[str, Any]:
        """A plain mapping of this record, ready to hand to a client."""
        return {
            "sys_id": self.sys_id,
            "table": self.table,
            "fields": dict(self.fields),
            "display_values": dict(self.display_values),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, table: str = "") -> "Record":
        """Build a record from a raw Table API result."""
        fields = {
            key: value
            for key, value in payload.items()
            if not key.startswith("sys_") or key in ("sys_id", "sys_created_on", "sys_updated_on")
        }
        display_values = {
            key[len("display_value:") :]: str(value)
            for key, value in payload.items()
            if key.startswith("display_value:")
        }
        return cls(
            sys_id=str(payload.get("sys_id", "")),
            table=str(payload.get("__table", table)),
            fields=fields,
            display_values=display_values,
        )


@dataclass(frozen=True)
class RecordPage:
    """A page of records plus the paging metadata that came with it."""

    records: tuple[Record, ...]
    total: int | None = None
    offset: int = 0
    limit: int = DEFAULT_LIMIT

    def __len__(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class Relation:
    """One CMDB relationship edge between two configuration items."""

    parent_sys_id: str
    child_sys_id: str
    type_sys_id: str
    type_label: str = ""
    parent_table: str = ""
    child_table: str = ""

    def to_dict(self) -> dict[str, Any]:
        """A plain mapping of this relation."""
        return {
            "parent_sys_id": self.parent_sys_id,
            "child_sys_id": self.child_sys_id,
            "type_sys_id": self.type_sys_id,
            "type_label": self.type_label,
            "parent_table": self.parent_table,
            "child_table": self.child_table,
        }


@dataclass(frozen=True)
class GraphNode:
    """A configuration item reached during graph traversal."""

    sys_id: str
    table: str
    name: str = ""
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        """A plain mapping of this node."""
        return {
            "sys_id": self.sys_id,
            "table": self.table,
            "name": self.name,
            "depth": self.depth,
        }
