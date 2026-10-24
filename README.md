# snowmcp — a consolidated ServiceNow MCP server

One MCP server for a ServiceNow instance. **Eleven tools** instead of the
17–500 that other ServiceNow MCP servers expose, with a local store that
remembers what it learns.

## Why eleven tools

Every ServiceNow MCP server in the wild exposes one tool per operation:
`sn_query`, `sn_get`, `sn_create`, `sn_update`, `sn_delete`, `sn_aggregate`,
`sn_schema`, `sn_relationships`, `sn_attach`, `sn_syslog`, … and the list
goes on. That is the wrong shape for an agent. Each tool's schema competes
for context, and the model has to work out which of 500 names to reach for
before it can do anything.

Here each tool covers a **domain**, and an `action` parameter selects the
operation. One schema does the work of many, and a single call can carry a
whole job — `sn_write` with `action=batch` applies many changes in one HTTP
request instead of one call per change.

| Tool | Read-only | What it covers |
|---|---|---|
| `sn_read` | yes | query / get / count records on any table |
| `sn_write` | no (destructive) | create / update / delete / batch |
| `sn_aggregate` | yes | stats and grouped statistics |
| `sn_schema` | yes | tables, fields, CMDB classes, field references |
| `sn_graph` | yes | Service Graph: relations, traverse, dependents, impact, CSDM |
| `sn_catalog` | no | catalog items, categories, variables, ordering |
| `sn_files` | no | attachments: list, upload, download, delete |
| `sn_code` | yes | the instance's own scripts, rules, policies, ACLs |
| `sn_ops` | yes | system log, health, jobs, properties, stats |
| `sn_local` | no | the local store: notes, cache, saved queries, journal, undo |
| `sn_admin` | no | update sets, scripts, ATF tests, users, groups, roles |

Read-only tools carry `readOnlyHint: true`, so a client running with
`trust: untrusted` only asks for approval on the tools that can actually
change the instance.

## What it stores

`sn_local` is the server's own memory, all local — nothing leaves the box:

- **knowledge base** — markdown notes the agent writes and re-reads
- **record cache** — records already fetched, so a second lookup costs no
  API call
- **saved queries** — a named query becomes one call later, not ten
- **call history** — what the agent already did, so it does not do it twice
- **write journal** — every applied write, with a plan to revert it

## Safety

- Every write needs `confirm=true`. The server refuses without it.
- `SN_READ_ONLY=true` refuses every write.
- `SN_ALLOWED_TABLES` / `SN_DENIED_TABLES` restrict which tables may be touched.
- `SN_MAX_BATCH` bounds a batch.
- The instance URL must be `https://` (or `http://` for local development).
- Every write is journalled; `sn_local action=undo` reverts it.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

## Configure

Copy `.env.example` to your environment and fill it in.

| Variable | Meaning |
|---|---|
| `SN_INSTANCE_URL` | `https://yourcompany.service-now.com` (required) |
| `SN_USERNAME` / `SN_PASSWORD` | basic auth |
| `SN_OAUTH_CLIENT_ID` / `SN_OAUTH_CLIENT_SECRET` / `SN_OAUTH_TOKEN_URL` | OAuth2 client credentials (instead of basic) |
| `SN_READ_ONLY` | `true` refuses every write |
| `SN_ALLOWED_TABLES` | comma-separated allow list |
| `SN_DENIED_TABLES` | comma-separated deny list |
| `SN_REQUIRE_CONFIRM` | `false` drops the `confirm=true` requirement |
| `SN_MAX_BATCH` | maximum operations in one batch (default 100) |
| `SN_STORE_PATH` | where the local store lives |
| `SN_TIMEOUT` | HTTP timeout in seconds (default 60) |

## Run

```bash
.venv/bin/snowmcp            # stdio
.venv/bin/python -m snowmcp  # the same
```

## Use it from Hermes

```yaml
mcp_servers:
  servicenow:
    command: "/home/agent/projects/snowmcp/.venv/bin/snowmcp"
    env:
      SN_INSTANCE_URL: "${env:SN_INSTANCE_URL}"
      SN_USERNAME: "${env:SN_USERNAME}"
      SN_PASSWORD: "${env:SN_PASSWORD}"
    trust: untrusted
    timeout: 120
```

`trust: untrusted` makes Hermes ask for approval on any write-capable tool
call. The server's own `confirm=true` requirement still applies on top.

## Architecture

Clean Architecture, dependencies pointing strictly inward:

```
src/snowmcp/domain/          business rules, value objects, policy. No framework.
src/snowmcp/application/     use cases, ports, endpoint policy.
src/snowmcp/adapters/        HTTP transport, SQLite store, MCP surface.
src/snowmcp/infrastructure/  configuration and the composition root.
```

`tests/qa/test_architecture.py` parses every import and fails the build on an
outward dependency, so the rule is enforced rather than merely described.

## Development

```bash
make setup      # uv venv + pytest, pytest-cov, mutmut, hypothesis
make test       # the suite
make coverage   # 100% branch coverage, enforced
make mutation   # mutation testing, zero survivors required
make gate       # both
```

The mutation gate is the one that matters. Coverage says a line ran; only
mutation testing says a wrong answer would have been caught.

> `mutmut` caches its verdicts in `mutants/`. After changing a test, run
> `rm -rf mutants` or the next run replays stale results.

## Licence

MIT.
