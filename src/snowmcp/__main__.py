"""Entry point: run the MCP server over stdio."""

from __future__ import annotations

import sys

from snowmcp.adapters.mcp.server import build_server
from snowmcp.infrastructure.config import load_settings
from snowmcp.infrastructure.wiring import build_services


def main() -> int:
    """Start the server on stdio."""
    settings = load_settings()
    try:
        settings.validate()
    except Exception as exc:  # noqa: BLE001 - reported to stderr, then exit
        print(f"snowmcp: {exc}", file=sys.stderr)
        return 2
    services = build_services(settings)
    build_server(services).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
