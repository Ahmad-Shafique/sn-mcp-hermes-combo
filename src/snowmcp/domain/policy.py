"""Write and read safety policy.

These controls are what make an agent's writes safe to run unattended: a
read-only mode, table allow/deny lists, a confirmation requirement for
destructive operations, and a bound on batch size.
"""

from __future__ import annotations

from dataclasses import dataclass

from snowmcp.domain.errors import SafetyGuardError

DEFAULT_MAX_BATCH = 100


@dataclass(frozen=True)
class WritePolicy:
    """What the server is allowed to change."""

    read_only: bool = False
    allowed_tables: frozenset[str] = frozenset()
    denied_tables: frozenset[str] = frozenset()
    require_confirm: bool = True
    max_batch: int = DEFAULT_MAX_BATCH

    def check_read(self, table: str) -> None:
        """Refuse a read of a table the policy excludes."""
        self._check_table(table)

    def check_write(self, table: str, *, confirmed: bool = False) -> None:
        """Refuse a write that the policy does not allow."""
        if self.read_only:
            raise SafetyGuardError("server is in read-only mode")
        self._check_table(table)
        if self.require_confirm and not confirmed:
            raise SafetyGuardError(
                f"write to {table!r} needs confirmation: pass confirm=true"
            )

    def check_batch(self, count: int) -> None:
        """Refuse a batch larger than the configured bound."""
        if count > self.max_batch:
            raise SafetyGuardError(
                f"batch of {count} exceeds the limit of {self.max_batch}"
            )

    def _check_table(self, table: str) -> None:
        if table in self.denied_tables:
            raise SafetyGuardError(f"table {table!r} is denied by policy")
        if self.allowed_tables and table not in self.allowed_tables:
            raise SafetyGuardError(f"table {table!r} is not in the allow list")
