"""The container of use cases.

This lives in the application layer because it is the application layer's
public shape: what a caller can ask for. The composition root in
``infrastructure`` builds one of these; the MCP adapter consumes one.

Keeping it here is what lets the dependency arrow point inward: the adapter
knows the application, and never the other way round.
"""

from __future__ import annotations

from dataclasses import dataclass

from snowmcp.application.graph import GraphService
from snowmcp.application.local import (
    CacheService,
    HistoryService,
    KnowledgeService,
    SavedQueryService,
    UndoService,
)
from snowmcp.application.records import AggregateService, RecordService, SchemaService
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)


@dataclass(frozen=True)
class Services:
    """Every use case the MCP surface needs."""

    records: RecordService
    aggregate: AggregateService
    schema: SchemaService
    graph: GraphService
    catalog: CatalogService
    files: FileService
    code: CodeService
    ops: OpsService
    admin: AdminService
    knowledge: KnowledgeService
    cache: CacheService
    saved_queries: SavedQueryService
    history: HistoryService
    undo: UndoService
