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

## How this relates to ServiceNow's own MCP servers

ServiceNow ships **official** MCP servers, and that changes what a
third-party server is for:

| Server | What it is |
|---|---|
| **MCP Server Console** (`sn_mcp_server`) | A platform product for building MCP servers on an instance. Exposes any REST API, AI skills, subflows, actions and Knowledge Graph schemas as tools. Streamable HTTP at `https://<instance>/sncapps/mcp-server/mcp/<name>`, OAuth 2.0. |
| **ITSM MCP Server** (`sn_itsm_mcp_server`) | First-party ITSM tools: `incident.get_details`, `incident.modify`, `change.lifecycle`, `change.analyze`, `change.query`, `change.relation`, requester tools. |
| **CSM MCP Server** | `get_case_tasks`, `get_customer_service_cases`, `case_summarization`, `resolution_notes_generation`, `sentiment_analysis`. |
| **MCP for Enterprise Architecture** | Includes *Related Entities Resolver*, whose `traverse` mode does multi-level impact analysis from a single CI. |

This server does not compete on raw connectivity — ServiceNow already has
that covered. It exists for the gaps the first-party servers leave:

1. **One unified namespace across every table**, not one tool per domain and
   a choice of 500 names.
2. **A local store.** Notes, a record cache, saved queries, call history and
   a journalled write log with undo. Nothing above has one.
3. **A batch action** that applies many writes in one HTTP request.
4. **Schema-aware parameters** named after the documented `sysparm_*` query
   parameters, so behaviour is predictable.
5. **Client-side graph traversal** with resolved relationship-type labels.

## Endpoints it calls

Verified against ServiceNow's own API reference, not assumed.

| Area | Endpoint |
|---|---|
| Table API | `GET/POST/PUT/PATCH/DELETE /api/now/table/{table}` and `/{sys_id}` |
| Aggregate (stats) | `GET /api/now/stats/{table}` with `sysparm_aggregate` |
| Batch | `POST /api/now/v1/batch` with `rest_requests[]` (id, method, relative url, Base64 body) |
| CMDB class schema | `GET /api/now/cmdb/meta/{className}` — the only *documented* class-introspection endpoint |
| CMDB relations | `GET /api/now/table/cmdb_rel_ci` (the traversal table), types resolved from `cmdb_rel_type` |
| Attachments | `GET/POST/DELETE /api/now/attachment` |
| Service Catalog | `/api/sn_sc/servicecatalog/items`, `.../{sys_id}`, `.../{sys_id}/order_now` — note the API has **its own root**, not `/api/now/...` |
| Update sets | `GET/POST /api/now/table/sys_update_set` |
| Server-side script | **No documented REST endpoint exists.** Point `SN_SCRIPTED_REST_URL` at a Scripted REST API you control. |

Two things are deliberately *not* hardcoded, because ServiceNow's public
contract does not name them:

- `sys_csdm_domain_model` and `sys_csdm_context` are probed through
  `sys_db_object` first. If the instance does not have them, the tool says so
  plainly instead of returning a confusing 404.
- CMDB class field lists are read from the instance, never hardcoded — CSDM
  class models are extensible per instance.

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
| `SN_SCRIPTED_REST_URL` | path of a Scripted REST API that executes server-side script, e.g. `/api/sn_gsc/v1/execute` |
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
    command: "/home/agent/projects/snowmcp/.venv/bin/python"
    args: ["-m", "snowmcp"]
    env:
      PYTHONPATH: "/home/agent/projects/snowmcp/src"
      SN_INSTANCE_URL: "${env:SN_INSTANCE_URL}"
      SN_USERNAME: "${env:SN_USERNAME}"
      SN_PASSWORD: "${env:SN_PASSWORD}"
      SN_STORE_PATH: "/home/agent/.hermes/data/snowmcp/store.sqlite3"
    enabled: false
    trust: untrusted
    timeout: 120
```

It is registered in this profile's config with `enabled: false`. Set the
instance details in your profile's secret store, then flip `enabled` to
`true` (or run `hermes mcp test servicenow` to check the connection).

`trust: untrusted` makes Hermes ask for approval on any write-capable tool
call. The server's own `confirm=true` requirement still applies on top.

## Four test tiers

Tier 1 - unit: domain rules in isolation, no I/O.
Tier 2 - integration: real components against real collaborators.
Tier 3 - QA: whole-system, from the composition root, plus architecture.
Tier 4 - mutation: the tests must actually fail when the code is wrong.

There is a **fifth kind of test** that pays for itself, even though it is
not a tier of its own: the **contract test**. For each entry point that
talks to the outside world, assert the exact request it makes - the path,
the method, every query parameter, the body - not only what comes back.
Result-level tests pass while the request quietly changes shape. Contract
tests catch that, and they are what closes most mutation survivors.

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
make mutation   # mutation testing + the score gate
make gate       # both
```

The mutation gate reports a **score** and enforces a floor
(`MIN_MUTATION_SCORE`, default 80). It is a ratchet: raise it as survivors
are closed, never lower it.

```bash
.venv/bin/python scripts/mutation_gate.py --min-score 80 --json
```

**Scope:** the mutation gate covers `src/snowmcp/domain/` and
`src/snowmcp/application/` — the business rules and use cases. The adapters
(transport, SQLite store, MCP surface) are excluded by an explicit
`only_mutate` in `pyproject.toml`, because a mutant there is a changed
default limit or a renamed dict key rather than a wrong rule, and the
contract tests already pin those exactly. The scope is declared in the
config so the score is never mistaken for a full-tree number.

Coverage says a line ran; only mutation testing says a wrong answer would
have been caught. Most surviving mutants are *argument* mutants - a changed
default, a removed keyword argument - which is why the contract tests
(`tests/integration/test_*_contracts.py`) matter as much as the unit tests.

> `mutmut` caches its verdicts in `mutants/`. After changing a test, run
> `rm -rf mutants` or the next run replays stale results. A full scoped run
> takes about an hour on four cores, so run it in the background.

## Licence

MIT.
