"""The composition root.

The only place that knows every concrete class. Everything inward of here
depends on ports; this module depends on both.
"""

from __future__ import annotations

from snowmcp.adapters.http.client import ServiceNowClient
from snowmcp.adapters.store.sqlite import SQLiteStore
from snowmcp.application.container import Services
from snowmcp.application.graph import GraphService
from snowmcp.application.local import (
    CacheService,
    HistoryService,
    KnowledgeService,
    SavedQueryService,
    UndoService,
)
from snowmcp.application.ports import InstanceGateway
from snowmcp.application.records import AggregateService, RecordService, SchemaService
from snowmcp.application.services import (
    AdminService,
    CatalogService,
    CodeService,
    FileService,
    OpsService,
)
from snowmcp.domain.policy import WritePolicy
from snowmcp.infrastructure.config import Settings


def build_gateway(settings: Settings) -> InstanceGateway:
    """Build the transport for the configured instance."""
    return ServiceNowClient(
        settings.instance_url,
        username=settings.username,
        password=settings.password,
        oauth_client_id=settings.oauth_client_id,
        oauth_client_secret=settings.oauth_client_secret,
        oauth_token_url=settings.oauth_token_url,
        timeout=settings.timeout,
        max_bytes=settings.max_bytes,
    )


def build_services(
    settings: Settings,
    *,
    gateway: InstanceGateway | None = None,
    store: SQLiteStore | None = None,
) -> Services:
    """Wire every use case to its concrete adapters."""
    instance = gateway if gateway is not None else build_gateway(settings)
    local = store if store is not None else SQLiteStore(settings.resolved_store_path)
    policy: WritePolicy = settings.policy
    return Services(
        records=RecordService(instance, policy, journal=local),
        aggregate=AggregateService(instance, policy),
        schema=SchemaService(instance, policy),
        graph=GraphService(instance, policy),
        catalog=CatalogService(instance, policy),
        files=FileService(instance, policy),
        code=CodeService(instance, policy),
        ops=OpsService(instance, policy),
        admin=AdminService(instance, policy),
        knowledge=KnowledgeService(local),
        cache=CacheService(local),
        saved_queries=SavedQueryService(local, instance),
        history=HistoryService(local),
        undo=UndoService(local, instance),
    )
