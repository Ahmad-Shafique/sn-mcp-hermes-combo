# Running snowmcp inside Hermes

`snowmcp` is a stdio MCP server. Hermes starts it as a subprocess and talks to
it over stdio; the instance credentials are passed as environment variables,
never on the command line.

## 1. Install

```bash
cd ~/projects/snowmcp
make setup          # uv venv + pytest, pytest-cov, mutmut, hypothesis
```

`make setup` creates `.venv/`. If you would rather use plain pip:

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

## 2. Register it with Hermes

`hermes mcp add` discovers the tools and writes the config entry:

```bash
hermes mcp add servicenow \
  --command ~/projects/snowmcp/.venv/bin/python \
  --env PYTHONPATH=~/projects/snowmcp/src \
  --env SN_INSTANCE_URL=https://yourcompany.service-now.com \
  --env SN_USERNAME=your_username \
  --env SN_PASSWORD=your_password \
  --env SN_STORE_PATH=~/.hermes/data/snowmcp/store.sqlite3 \
  --args -m snowmcp
```

`--args` must be last. The equivalent hand-written `~/.hermes/config.yaml`
entry:

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

Keep the credentials in the profile's secret store (`~/.hermes/.env`) and
reference them as `${env:SN_PASSWORD}`. Hermes resolves those at start-up;
a literal password in `config.yaml` is a password in a file that gets copied,
synced and committed by accident.

## 3. Check the connection

```bash
hermes mcp test servicenow     # connect and list discovered tools
hermes mcp list                # what is configured
hermes mcp configure servicenow  # choose which tools to expose
```

## 4. Trust and approvals

`trust: untrusted` makes Hermes ask for approval on any write-capable tool
call. The server's own `confirm=true` requirement still applies underneath, so
a write has to pass two gates.

Read-only tools carry `readOnlyHint: true`, so only the seven
write-capable tools (`sn_write`, `sn_catalog`, `sn_files`, `sn_state`,
`sn_journal`, `sn_admin`) trigger an approval prompt.

## 5. Safety switches

Set these in the server's environment:

| Variable | Effect |
|---|---|
| `SN_READ_ONLY=true` | refuses every write, at the server, regardless of approvals |
| `SN_ALLOWED_TABLES=incident,change_request` | only these tables may be touched |
| `SN_DENIED_TABLES=sys_user` | these tables may never be touched |
| `SN_REQUIRE_CONFIRM=false` | drops the `confirm=true` requirement (do not) |
| `SN_MAX_BATCH=100` | bounds a batch |

Start read-only. Widen the allow list only when you need to.

## 6. The local store

`SN_STORE_PATH` points at a SQLite file that holds the server's own memory:
markdown notes, a record cache, saved queries, call history, and a journal of
every applied write with a plan to revert it.

Nothing in that store leaves the machine. It is the one part of the system
that works with no instance credentials at all, which makes it the right place
to keep working notes while the connection is being set up.

## Troubleshooting

**The server starts but every call fails with a connection error.** Check
`SN_INSTANCE_URL` is the full origin including `https://` and no trailing path,
and that the credentials belong to an account with REST role access.

**`sn_write` refuses.** It requires `confirm=true`. This is deliberate.

**A table call returns a confusing 404 for a CSDM table.** `sys_csdm_domain_model`
and `sys_csdm_context` are probed through `sys_db_object` first; if the
instance lacks them the tool says so plainly rather than returning a bare 404.

**Writes are not showing up in `sn_journal`.** The journal is written by the
same process that applied the write. If the server was restarted mid-call the
entry may not exist - check `sn_ops action=health` for the current store path.
