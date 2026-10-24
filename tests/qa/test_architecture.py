"""Tier 3 - QA tests. The architecture itself is under test.

Robert C. Martin's Dependency Rule: source code dependencies point only
inward. A layered architecture nobody checks is a layered architecture that
erodes, so this parses every import and fails on any outward dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "snowmcp"

# Layer -> the layers it may import (itself plus anything inward).
ALLOWED = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "adapters": {"domain", "application", "adapters"},
    "infrastructure": {"domain", "application", "adapters", "infrastructure"},
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def _layer_of(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "snowmcp":
        return parts[1]
    return None


@pytest.mark.qa
@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_does_not_import_outward(layer: str) -> None:
    violations: list[str] = []
    for module_path in sorted((SRC / layer).rglob("*.py")):
        for imported in _imports(module_path):
            imported_layer = _layer_of(imported)
            if imported_layer is None:
                continue
            if imported_layer not in ALLOWED[layer]:
                violations.append(
                    f"{module_path.relative_to(SRC)} imports {imported} "
                    f"(layer '{imported_layer}' is outward of '{layer}')"
                )
    assert not violations, "Dependency Rule violated:\n" + "\n".join(violations)


@pytest.mark.qa
def test_every_layer_directory_exists() -> None:
    """A missing layer means the architecture was never actually built."""
    for layer in ALLOWED:
        assert (SRC / layer).is_dir(), f"missing layer: {layer}"


@pytest.mark.qa
def test_the_domain_layer_imports_no_outer_project_modules() -> None:
    """The innermost layer stays free of framework and project coupling.

    Sibling imports inside ``domain`` are fine; reaching out to
    ``application``, ``adapters`` or ``infrastructure`` is not.
    """
    for module_path in sorted((SRC / "domain").rglob("*.py")):
        for imported in _imports(module_path):
            imported_layer = _layer_of(imported)
            assert imported_layer in (None, "domain"), (
                f"{module_path.name} imports {imported}; the domain layer "
                "must not depend on outer layers"
            )


@pytest.mark.qa
def test_the_domain_layer_imports_no_third_party_framework() -> None:
    """The domain layer stays portable: no mcp, no urllib, no sqlite."""
    forbidden = {"mcp", "urllib", "sqlite3", "http", "requests", "httpx"}
    for module_path in sorted((SRC / "domain").rglob("*.py")):
        for imported in _imports(module_path):
            root = imported.split(".")[0]
            assert root not in forbidden, (
                f"{module_path.name} imports {imported}; the domain layer "
                "must not depend on a framework"
            )


@pytest.mark.qa
def test_the_application_layer_does_not_import_adapters() -> None:
    """Use cases depend on ports, never on a concrete transport."""
    for module_path in sorted((SRC / "application").rglob("*.py")):
        for imported in _imports(module_path):
            assert not imported.startswith("snowmcp.adapters"), (
                f"{module_path.name} imports {imported}; the application layer "
                "must depend on ports, not adapters"
            )


@pytest.mark.qa
def test_the_mcp_adapter_does_not_import_infrastructure() -> None:
    """The protocol adapter is wired by the composition root, not by itself."""
    for module_path in sorted((SRC / "adapters" / "mcp").rglob("*.py")):
        for imported in _imports(module_path):
            assert not imported.startswith("snowmcp.infrastructure"), (
                f"{module_path.name} imports {imported}; the adapter must not "
                "reach into the composition root"
            )
