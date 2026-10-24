"""The consolidated capability vocabulary.

Every existing ServiceNow MCP server exposes tens to hundreds of individual
tools. That is the wrong shape for an agent: every schema competes for
context, and the model has to learn which of 500 names to reach for.

This module defines the alternative: a small number of *domain* tools, each
carrying an ``action`` enum. The vocabulary lives in the domain layer because
it is the shared language of the whole server.
"""

from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    """Base for every action enum."""


class RecordAction(Action):
    """Generic Table API record operations."""

    QUERY = "query"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BATCH = "batch"
    COUNT = "count"


class AggregateAction(Action):
    """Aggregate / stats operations."""

    STATS = "stats"
    GROUP = "group"


class SchemaAction(Action):
    """Table metadata and schema introspection."""

    TABLES = "tables"
    FIELDS = "fields"
    CLASS = "class"
    REFERENCES = "references"
    DICTIONARY = "dictionary"


class GraphAction(Action):
    """CMDB Service Graph traversal and impact analysis."""

    RELATIONS = "relations"
    TRAVERSE = "traverse"
    IMPACT = "impact"
    DEPENDENTS = "dependents"
    CSDM = "csdm"


class CatalogAction(Action):
    """Service Catalog browsing and ordering."""

    ITEMS = "items"
    CATEGORIES = "categories"
    ORDER = "order"
    VARIABLES = "variables"


class FileAction(Action):
    """Attachment operations."""

    LIST = "list"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    DELETE = "delete"


class CodeAction(Action):
    """Instance artefact discovery and search."""

    SEARCH = "search"
    LIST = "list"
    READ = "read"
    WHERE_USED = "where_used"


class OpsAction(Action):
    """Instance operations and health."""

    LOG = "log"
    HEALTH = "health"
    JOBS = "jobs"
    PROPERTIES = "properties"
    STATS = "stats"


class LocalAction(Action):
    """Local storage: knowledge base, record cache, saved queries, journal."""

    NOTE_WRITE = "note_write"
    NOTE_READ = "note_read"
    NOTE_SEARCH = "note_search"
    NOTE_LIST = "note_list"
    NOTE_DELETE = "note_delete"
    CACHE_GET = "cache_get"
    CACHE_PUT = "cache_put"
    CACHE_LIST = "cache_list"
    SAVED_SAVE = "saved_save"
    SAVED_RUN = "saved_run"
    SAVED_LIST = "saved_list"
    HISTORY = "history"
    JOURNAL = "journal"
    UNDO = "undo"


class AdminAction(Action):
    """Administrative surfaces: update sets, scripts, tests, directory."""

    UPDATE_SETS = "update_sets"
    SET_UPDATE_SET = "set_update_set"
    SCRIPT = "script"
    ATF = "atf"
    USERS = "users"
    GROUPS = "groups"
    ROLES = "roles"
    MEMBERSHIPS = "memberships"
