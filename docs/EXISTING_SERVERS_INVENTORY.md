# ServiceNow MCP Server Capability Inventory

All three repos were cloned locally and read at source level. Tool names and endpoint paths are
quoted verbatim from source. Anything not directly observed is marked **UNVERIFIED**.

- `aartiq/servicenow-mcp` → cloned to `/home/agent/snmcp/A_repo` (npm package `nowaikit`, v4.21.0)
- `IvanBBaev/servicenow-mcp-ai` → `/home/agent/snmcp/I_repo` (npm `servicenow-mcp-ai`, v3.0.0)
- `seemsindie/servicenow-mcp-server` → `/home/agent/snmcp/S_repo` (Bun/TS, v0.4.0)

---

## 1. `aartiq/servicenow-mcp` (NowAIKit)

### 1.1 Namespace / prefix convention

**No prefix.** Tool names are bare snake_case verbs, globally unique across ~80 module files.
Observed convention: `<verb>_<noun>` where verb ∈ {list, get, create, update, delete, search,
run, set, publish, commit, order, approve, reject, resolve, close, add, remove, trigger, fire,
execute, upload, retrieve, compare, check, find, preview, export, import, bulk_, ml_, cmdb_,
servicenow…}. Two meta-tools exist: `search_tools` and `run_tool`.

Counted 508 tool-name literals across `src/tools/*.ts` (the "500+" claim). `docs/TOOLS.md`
documents 277 of them grouped into 32 sections.

### 1.2 Representative tool names by domain (verbatim)

| Domain | Tools (from `src/tools/<module>.ts`) |
|---|---|
| Core / generic (`core.ts`) | `query_records`, `get_record`, `create_record`, `update_record`, `delete_record`, `get_table_schema`, `get_mandatory_fields`, `validate_query`, `get_user`, `get_group`, `search_cmdb_ci`, `get_cmdb_ci`, `list_relationships`, `list_discovery_schedules`, `list_mid_servers`, `list_active_events`, `cmdb_health_dashboard`, `service_mapping_summary`, `natural_language_search`, `natural_language_update`, `list_instances`, `switch_instance`, `get_current_instance`, `create_ci_relationship`, `cmdb_impact_analysis`, `run_discovery_scan` |
| ITSM incident (`incident.ts`) | `create_incident`, `get_incident`, `update_incident`, `resolve_incident`, `close_incident`, `add_work_note`, `add_comment` |
| ITSM problem / change / task | `create_problem`, `get_problem`, `update_problem`, `resolve_problem`; `create_change_request`, `get_change_request`, `update_change_request`, `list_change_requests`, `submit_change_for_approval`, `close_change_request`, `schedule_cab_meeting`; `get_task`, `list_my_tasks`, `update_task`, `complete_task` |
| CMDB (`core.ts`, `cmdb-reconciliation.ts`, `service-mapping.ts`) | `cmdb_find_duplicates`, `cmdb_find_orphans`, `cmdb_find_stale`, `cmdb_reconcile`, `cmdb_impact_analysis`, `list_application_services`, `cmdb_services_for_ci`, `cmdb_find_unmapped_cis`, `suggest_ci_class` |
| ITOM | `list_discovery_schedules`, `list_mid_servers`, `list_active_events`, `run_discovery_scan`, `service_mapping_summary`; `platform-ops.ts`: `list_scan_suites`, `get_instance_scan_findings`, `get_ecc_queue`, `resubmit_ecc_probe`, `run_fix_script` |
| HRSD (`hrsd.ts`) | `create_hr_case`, `get_hr_case`, `update_hr_case`, `list_hr_cases`, `close_hr_case`, `list_hr_services`, `get_hr_service`, `get_hr_profile`, `update_hr_profile`, `list_hr_tasks`, `create_hr_task`, `get_hr_case_activity`, `create_onboarding_case`, `create_offboarding_case`, `get_hr_lifecycle_events`, `list_hr_document_templates` |
| CSM (`csm.ts`) | `create_csm_case`, `get_csm_case`, `update_csm_case`, `list_csm_cases`, `close_csm_case`, `get_csm_account`, `list_csm_accounts`, `get_csm_contact`, `list_csm_contacts`, `get_csm_case_sla`, `list_csm_products` |
| Service Catalog (`catalog.ts`, `catalog-fulfillment.ts`) | `list_catalog_items`, `search_catalog`, `get_catalog_item`, `create_catalog_item`, `update_catalog_item`, `order_catalog_item`, `create_approval_rule`, `create_catalog_variable`, `create_catalog_ui_policy`, `get_request_item`, `update_request_item`, `list_catalog_tasks`, `complete_catalog_task`, `list_catalog_categories`, `create_catalog_category` |
| Flow Designer (`flow.ts`) | `list_flows`, `get_flow`, `trigger_flow`, `get_flow_execution`, `list_flow_executions`, `list_subflows`, `get_subflow`, `list_action_instances`, `get_process_automation`, `list_process_automations`, `create_flow`, `create_subflow`, `create_flow_action`, `publish_flow`, `update_flow`, `test_flow`, `get_flow_error_log` |
| Platform development (`script.ts`, `workspace.ts`, `portal.ts`) | `list_business_rules`, `create_business_rule`, `list_script_includes`, `create_script_include`, `list_client_scripts`, `create_client_script`, `list_ui_policies`, `create_ui_policy`, `list_ui_actions`, `create_ui_action`, `list_acls`, `create_acl`, `list_changesets`, `commit_changeset`, `publish_changeset`; `list_uib_pages`, `create_uib_page`, `list_uib_components`, `list_uib_data_brokers`, `list_workspaces`, `create_workspace`; `list_portals`, `list_portal_pages`, `list_portal_widgets`, `create_portal_widget`, `list_ux_apps`, `list_ux_pages` |
| Attachments (`notification.ts`) | `list_attachments`, `get_attachment_metadata`, `read_attachment`, `copy_attachment`, `delete_attachment`, `upload_attachment` |
| Knowledge (`knowledge.ts`) | `list_knowledge_bases`, `search_knowledge`, `get_knowledge_article`, `create_knowledge_article`, `update_knowledge_article`, `publish_knowledge_article`, `retire_knowledge_article` |
| Directory / users (`user.ts`, `access-admin.ts`) | `list_users`, `create_user`, `update_user`, `list_groups`, `create_group`, `update_group`, `add_user_to_group`, `remove_user_from_group`; `list_user_roles`, `grant_role`, `revoke_role`, `create_role`, `deactivate_user`, `create_delegation`, `list_group_members`, `get_user_entitlements` |
| Ops / system-log (`reporting.ts`) | `get_sys_log`, `list_scheduled_jobs`, `get_scheduled_job`, `create_scheduled_job`, `update_scheduled_job`, `trigger_scheduled_job`, `list_job_run_history`, `list_reports`, `get_report`, `run_aggregate_query`, `trend_query`, `get_performance_analytics` |
| ATF testing (`atf.ts`) | `list_atf_suites`, `get_atf_suite`, `run_atf_suite`, `list_atf_tests`, `get_atf_test`, `run_atf_test`, `get_atf_suite_result`, `list_atf_test_results`, `get_atf_failure_insight` |
| Impact analysis (`impact-analysis.ts`) | `list_table_config`, `find_field_references`, `find_script_references`, `find_update_sets`, `find_property_usage` |
| Update sets (`updateset.ts`) | `get_current_update_set`, `list_update_sets`, `create_update_set`, `switch_update_set`, `complete_update_set`, `preview_update_set`, `export_update_set`, `ensure_active_update_set` |
| Local sync (`local-sync.ts`) | `list_supported_artifacts`, `pull_artifact`, `push_artifact`, `sync_status` |
| Bundles (multi-call outcome tools) | `investigate_incident`, `change_readiness`, `service_health` |

### 1.3 REST endpoints and query params

Base: `${baseUrl}/api/now/...`. All Table API calls go through `client.queryRecords()`
(`src/servicenow/client.ts`), which sets exactly these params:

```
sysparm_query, sysparm_fields, sysparm_display_value ("true"|"all"),
sysparm_limit (Math.min(limit,1000), default "10"), sysparm_offset,
sysparm_exclude_reference_link
```
`orderBy` is folded into `sysparm_query` as `^ORDERBY<field>` / `^ORDERBYDESC<field>`.

| Capability | Method + path | Key params / tables |
|---|---|---|
| Generic read | `GET /api/now/table/{table}` | above |
| Generic write | `POST /api/now/table/{table}` | JSON body of fields |
| Generic update | `PATCH /api/now/table/{table}/{sysId}` | |
| Generic delete | `DELETE /api/now/table/{table}/{sysId}` | |
| Single record | `GET /api/now/table/{table}/{sysId}` | `sysparm_fields`, `sysparm_display_value` |
| Current user | `GET /api/now/ui/user/current_user` | least-privilege auth check |
| Aggregate / stats | `GET /api/now/stats/{table}` | `sysparm_group_by`, `sysparm_count=true`, `sysparm_query`, `sysparm_display_value`, `sysparm_avg_fields`, `sysparm_sum_fields`, `sysparm_min_fields`, `sysparm_max_fields` |
| Batch | `POST /api/now/v1/batch` | ≤50 operations per batch (`batch_request` enforces "Maximum 50 operations per batch") |
| Attachment upload | `POST /api/now/attachment/file` | `table_name`, `table_sys_id`, `file_name` |
| Attachment read | `GET /api/now/attachment/{id}` + `GET /api/now/attachment/{id}/file` | |
| Catalog item | `GET /api/sn_sc/servicecatalog/items/{sysId}` | |
| Catalog order | `POST /api/sn_sc/servicecatalog/items/{sys_id}/order_now` | |
| Performance Analytics | `GET /api/now/pa/scorecards`, `GET /api/now/pa/widget/{sys_id}` | |
| Reporting | `GET /api/now/reporting` | |
| ATF run | `POST /api/sn_cicd/testsuite/run?test_suite_sys_id={sysId}` | via `client.callNowAssist`; the comment states the old `/api/now/atf/runner/*` path "does not exist" |
| AI search / NLQ | `POST /api/now/ai_search/search`, `POST /api/sn_nl_text_to_value/text_query` | |
| Now Assist skill | `POST /api/sn_assist/skill/invoke` | |
| Virtual Agent | `GET /api/sn_cs/topic`, `GET /api/sn_cs/bot/integration` | |
| ML training | `POST /api/now/ml/solution/{sol.sys_id}/train` | |
| Background script | `POST /api/now/sp/background_script` | |
| Public docs (SSRF-guarded) | `POST /api/khub/clustered-search` | host allowlist `www.servicenow.com`, `servicenow.com`, `docs.servicenow.com` |
| Script exec | `SCRIPT_EXEC_ENDPOINT` env (e.g. `/api/x_nowaikit/exec`) | external scripted REST API |

Tables per capability area (from source): incident→`incident`; change→`change_request`; CMDB→
`cmdb_ci`, `cmdb_rel_ci`, `cmdb_ci_service`, `cmdb_class_info`, `cmdb_ci_service_auto`, `svc_ci_assoc`,
`sys_db_object`; knowledge→`kb_knowledge`, `kb_knowledge_base`; catalog→`sc_cat_item`, `sc_category`,
`sc_req_item`, `sc_task`, `sc_item_option_mtom`, `catalog_item`, `catalog_ui_policy`; flows→
`sys_hub_flow`, `sys_hub_subflow`, `sys_hub_flow_trigger`, `sys_hub_action_instance`,
`sys_hub_action_type_definition`, `sys_flow_context`, `pa_process`; scripting→`sys_script`,
`sys_script_include`, `sys_script_client`, `sys_ui_policy`, `sys_ui_action`, `sys_security_acl`,
`sys_update_set`; attachments→`sys_attachment`; users→`sys_user`, `sys_user_group`, `sys_user_grmember`,
`sys_user_has_role`, `sys_user_delegate`; ops→`syslog`, `syslog_app_scope`, `sysauto`, `sys_report`,
`sys_report_schedule`, `sysauto_trigger_log`; ATF→`sys_atf_test_suite`, `sys_atf_test`,
`sys_atf_test_suite_result`, `sys_atf_result`, `sys_atf_failure_insight`; HRSD→`sn_hr_core_case`,
`sn_hr_core_profile`, `sn_hr_core_service`, `sn_hr_core_task`, `sn_hr_core_document_template`,
`sn_hr_le_lifecycle_event`, `sys_journal_field`; CSM→`sn_customerservice_case`, `customer_account`,
`customer_contact`, `task_sla`; integration→`sys_rest_message`, `sys_rest_message_fn`,
`sys_transform_map`, `sys_transform_entry`, `sys_import_set`, `sys_import_set_run`, `sys_data_source`,
`sysevent`, `sysevent_register`, `oauth_entity`, `sys_alias`; ITAM→`alm_asset`, `alm_license`,
`ast_contract`; security→`sn_si_incident`, `sn_vul_entry`, `sn_risk_risk`, `sn_compliance_control`,
`sn_compliance_policy`, `sn_audit_result`, `sn_ti_observable`; agile→`rm_story`/`rm_epic` equivalents
(`m2m_story_dependencies`), `pm_project`.

### 1.4 Tool-package / role-based subsetting

Two independent axes that compose (`docs/TOOL_PACKAGES.md`, `src/tools/index.ts`):

1. **Discovery mode** — `MCP_TOOL_DISCOVERY` env: `lean` (core + `search_tools` + `run_tool`,
   ~13 tools), `core` (core CRUD only, no `search_tools`), unset (whole package).
2. **Package** — `MCP_TOOL_PACKAGE` env selects a role subset from `PACKAGE_TOOL_NAMES`
   (a `Record<string, string[]>` of literal tool names).

14 packages: `full` (500+), `service_desk` (23), `change_coordinator` (18), `knowledge_author` (12),
`catalog_builder` (11), `system_administrator` (55), `platform_developer` (41), `itom_engineer` (12),
`agile_manager` (12), `ai_developer` (18), `portal_developer` (35), `integration_engineer` (29),
`devops_engineer` (24), `itam_analyst` (10). (Counts are the doc's; actual unique-name counts
parsed from source: service_desk 23, change_coordinator 18, knowledge_author 13, catalog_builder 14,
system_administrator 83, platform_developer 59, itom_engineer 21, agile_manager 13, ai_developer 36,
portal_developer 37, integration_engineer 29, devops_engineer 24, itam_analyst 12.)

Mechanism: `getTools()` reads `process.env.MCP_TOOL_PACKAGE` / `MCP_TOOL_DISCOVERY`, filters
`ALL_TOOLS` by the allow-list, and returns `[SEARCH_TOOLS_DEF, ...filtered, ...dynamicTools]`.
`search_tools` scores name/description keyword matches (exact name +10, substring +5, description
+2); `run_tool` dispatches by exact name into the same `executeTool` handler, so capability guards
still apply.

### 1.5 Impact analysis (`src/tools/impact-analysis.ts`)

All read-only; each sub-query is individually guarded (`safeQuery` returns `{error}` instead of
failing the whole call). Tool set: `list_table_config`, `find_field_references`,
`find_script_references`, `find_update_sets`, `find_property_usage`.

Identifier validation: `assertIdentifier` allows only `^[a-z0-9_.]+$`; `assertSearchTerm` rejects
`^ = ,` so a crafted term cannot inject `^OR`/`^NQ`.

`SCRIPT_TABLES` (searched for textual references):
`sys_script`(field `script`, label `business_rules`), `sys_script_include`/`script_includes`,
`sys_script_client`/`client_scripts`, `sys_ui_action`/`ui_actions`, `sysauto_script`/`scheduled_jobs`,
`sys_script_fix`/`fix_scripts`, `sp_widget`/`widgets`.

- **`list_table_config`** — parallel queries: `sys_script` `collection={t}`; `sys_script_client`
  `table={t}`; `sys_ui_policy` `table={t}`; `sys_security_acl` `name={t}^ORnameSTARTSWITH{t}.`;
  `sys_ui_action` `table={t}`; `sys_data_policy2` `table={t}`; `sys_dictionary`
  `name={t}^elementISNOTEMPTY`. Returns `{table, summary{…counts}, business_rules, client_scripts,
  ui_policies, acls, ui_actions, data_policies, dictionary_fields}`.
- **`find_field_references`** — `sys_dictionary` query `name={t}^element={f}`; then for each
  SCRIPT_TABLES entry: `{field}LIKE{f}` (substring, documented as false-positive-prone).
  Returns `{table, field, total_references, dictionary, references}`.
- **`find_script_references`** — for each SCRIPT_TABLES entry: `{field}LIKE{name}`.
- **`find_update_sets`** — `sys_update_xml` query `target_nameLIKE{n}^ORnameLIKE{n}`, fields
  `sys_id,name,target_name,type,action,update_set`, grouped into `{update_set, changes}` counts.
- **`find_property_usage`** — `sys_properties` `name={n}` + script-table LIKE sweep.

### 1.6 Journal / undo and local knowledge base

**No journal-based undo in repo A.** No write journal, no revert tool, no local Markdown knowledge
base. The nearest analogues:
- `src/tools/updateset.ts` — update-set binding via the **`sys_user_preference`** row
  (`name=sys_update_set^user=javascript:gs.getUserID()`), explicitly *not* the shared per-scope
  `is_default` flag. `switch_update_set` PATCHes `sys_user_preference`, `create_update_set` POSTs it
  if absent, `ensure_active_update_set` auto-creates `sys_update_set` and points the caller at it.
- `src/tools/local-sync.ts` — pull/push of artifacts to local files, confined to `NOWAIKIT_SYNC_DIR`
  (when unset, pull returns content inline and push expects fields in the call). Supported tables
  map e.g. `sp_widget` → `{template:html, css:css, script:js, option_schema:json, demo_data:json}`,
  `sys_script_include`/`sys_script`/`sys_script_client`/`sys_ui_action`/`sys_ui_script`/`sysauto_script`
  → `{script:js}`, `sys_ui_page` → `{html:html, client_script:js, processing_script:js}`.
- `src/tools/bundles.ts` — one-call outcome tools, the opposite of undo (read-only assembly).

### 1.7 Update-set binding (`SN_UPDATE_SET`)

**`SN_UPDATE_SET` does not appear anywhere in repo A** (grepped all source + docs). Repo A has no
env-driven update-set binding; the caller must call `switch_update_set` / `ensure_active_update_set`
explicitly. Update-set state is read/written via the Table API on `sys_update_set` and
`sys_update_xml`; `export_update_set` returns a summary and points to the UI at `/sys_update_set.do`
rather than producing XML.

### 1.8 Safety controls

- **Permission tiers** (`src/utils/permissions.ts`): Tier 0 read; Tier 1 `WRITE_ENABLED`;
  Tier 2 `+CMDB_WRITE_ENABLED`; Tier 3 `+SCRIPTING_ENABLED`; Tier AI `NOW_ASSIST_ENABLED`;
  Tier ATF `ATF_ENABLED`; plus `FLUENT_ENABLED`. `requireWrite()`, `requireCmdbWrite()`,
  `requireScripting()`, `requireNowAssist()`, `requireAtf()`, `requireFluent()` throw
  `ServiceNowError` with codes `WRITE_NOT_ENABLED`, `CMDB_WRITE_NOT_ENABLED`,
  `SCRIPTING_NOT_ENABLED`, `NOW_ASSIST_NOT_ENABLED`, `ATF_NOT_ENABLED`, `FLUENT_NOT_ENABLED`.
- **Delegated auth can only narrow** the env ceiling: effective capability = (env AND delegated).
- **Guardrails** (`src/utils/guardrails.ts`): `NOWAIKIT_TABLE_DENYLIST` (tables that may never be
  written), `NOWAIKIT_FIELD_DENYLIST` (`"table.field"` or bare field), `NOWAIKIT_WRITE_SCOPE_PREFIX`
  (only tables matching an allowed prefix, e.g. `x_`). Built-in always-denied fields:
  `sys_user.user_password`, `sys_user.password`, `user_password`, `password`. Error code
  `WRITE_GUARDRAIL`. `assertDeleteAllowed` delegates to `assertWriteAllowed`.
- **Result-size guards**: `sysparm_limit` clamped to `Math.min(limit, 1000)`; default `10`;
  CMDB search clamps to 100; attachment fetch capped by `MAX_FETCH_BYTES = 50 * 1024 * 1024` (50 MB).
- **Retry/timeout**: `maxRetries` default 3, `retryDelayMs` default 1000, exponential backoff
  `retryDelayMs * 2^attempt`; per-request `AbortController` timeout. Non-idempotent writes are
  **never** auto-retried when no HTTP response was received (so a create can't be duplicated);
  401 triggers one forced re-auth + retry. Env: `MAX_RETRIES`, `RETRY_DELAY_MS`, `REQUEST_TIMEOUT_MS`
  (default 30000).
- **SSRF guard**: `src/tools/docs.ts` uses a host allowlist (`ALLOWED_DOC_HOSTS`) for the public docs
  fetch. No general outbound-URL guard in the client; a scripted-REST-API exec endpoint is
  operator-configured via `SCRIPT_EXEC_ENDPOINT`.
- **Tool annotations** are auto-derived from the name (`toolAnnotations`): destructive prefixes
  `delete_|retire_|remove_|close_|cancel_|reject_|rollback_` plus a named set; write prefixes
  `create_|update_|add_|set_|order_|submit_|publish_|commit_|trigger_|fire_|run_|execute_|bulk_|…`.

### 1.9 Test tooling & coverage

- **Vitest** (`vitest.config.ts`): `globals: true`, `environment: 'node'`,
  `setupFiles: ['./tests/setup.ts']`, coverage provider `v8`, reporters `text|json|html`,
  excludes `node_modules/`, `tests/`, `dist/`.
- 33 test files under `tests/` (unit dirs: `tools/`, `servicenow/`, `resources/`, `reports/`,
  `transport/`, `utils/`, `a2a/`, `cli/`, `direct/`), incl. `tests/tools/safety.test.ts`,
  `tests/tools/permissions.test.ts`, `tests/tools/updateset.test.ts`, `tests/tools/router.test.ts`,
  `tests/servicenow/retry-delegation.test.ts`, `tests/servicenow/attachment-read-copy.test.ts`.
- Scripts: `npm test` → `vitest run`; `npm run lint` → `eslint src tests`; `npm run type-check` → `tsc --noEmit`.
- CI (`.github/workflows/ci.yml`): Node 20.x/21.x matrix, `permissions: contents: read`, runs
  lint → type-check → build. **No coverage threshold gate and no coverage step in CI** — coverage is
  configured but not enforced. Also `.github/workflows/release.yml`.

---

## 2. `IvanBBaev/servicenow-mcp-ai`

### 2.1 Namespace / prefix convention

**Uniform `servicenow_` prefix** on every tool: `servicenow_<verb>_<noun>`. 100 `defineTool` specs
across `src/tools/*.ts` (README badge says "tools-100"; the "67 tools" figure in the task prompt is
not what the current README/source says). One name is a constant: `REVERT_TOOL = "servicenow_revert_write"`.

### 2.2 Representative tool names by domain (verbatim, from `src/tools/*.ts`)

| Domain | Tools |
|---|---|
| Table CRUD (`table.ts`) | `servicenow_query_table`, `servicenow_get_record`, `servicenow_create_record`, `servicenow_update_record`, `servicenow_upsert_record`, `servicenow_delete_record` |
| Schema (`meta.ts`) | `servicenow_describe_table`, `servicenow_list_tables` |
| Aggregate | `servicenow_aggregate` |
| Attachments (`attachment.ts`) | `servicenow_list_attachments`, `servicenow_get_attachment`, `servicenow_download_attachment`, `servicenow_upload_attachment`, `servicenow_delete_attachment` |
| Import set | `servicenow_get_import_set_row`, `servicenow_insert_import_set_row` |
| Batch | `servicenow_batch` |
| Service Catalog (`catalog.ts`) | `servicenow_list_catalogs`, `servicenow_list_catalog_categories`, `servicenow_list_catalog_items`, `servicenow_get_catalog_item`, `servicenow_order_catalog_item` |
| Change | `servicenow_list_changes`, `servicenow_get_change`, `servicenow_create_change`, `servicenow_update_change`, `servicenow_check_change_conflicts` |
| Knowledge | `servicenow_search_knowledge`, `servicenow_get_knowledge_article`, `servicenow_get_knowledge_highlights` |
| CMDB | `servicenow_list_cis`, `servicenow_get_ci`, `servicenow_create_ci`, `servicenow_update_ci`, `servicenow_get_cmdb_meta`, `servicenow_list_ci_relations`, `servicenow_identify_reconcile` |
| Scripts / impact | `servicenow_list_scripts`, `servicenow_get_script`, `servicenow_search_code`, `servicenow_describe_table_logic`, `servicenow_where_used`; codecheck: `servicenow_check_code_health`, `servicenow_lint_script`, `servicenow_lint_table` |
| Flows | `servicenow_list_flows`, `servicenow_get_flow`, `servicenow_get_flow_runs`, `servicenow_explain_flow`, `servicenow_trace_table_event` |
| Local KB / diagrams (`docs.ts`) | `servicenow_list_docs`, `servicenow_read_doc`, `servicenow_search_docs`, `servicenow_write_doc`, `servicenow_document_table`, `servicenow_document_app`, `servicenow_document_instance`, `servicenow_generate_er_diagram`, `servicenow_generate_table_flow` |
| Instance | `servicenow_compare_instances`, `servicenow_snapshot_instance`, `servicenow_review_upgrade` |
| Email | `servicenow_send_email`, `servicenow_get_email` |
| ATF | `servicenow_list_atf`, `servicenow_run_atf`, `servicenow_get_atf_result` |
| Revert / journal | `servicenow_list_writes`, `servicenow_revert_write` |
| Artifacts | `servicenow_list_artifacts`, `servicenow_get_artifact`, `servicenow_get_artifact_dependencies`, `servicenow_upsert_artifact`, `servicenow_explain_artifact` |
| Update sets | `servicenow_list_update_sets`, `servicenow_get_update_set`, `servicenow_compare_update_set`; cicd: `servicenow_commit_update_set` |
| Access | `servicenow_change_access`, `servicenow_explain_access` |
| Ops / system-log | `servicenow_read_ops`, `servicenow_check_data_health` |
| History | `servicenow_get_record_history`, `servicenow_get_task_context` |
| Properties | `servicenow_get_properties`, `servicenow_set_property` |
| Directory / users | `servicenow_lookup_directory` |
| UI | `servicenow_explain_portal`, `servicenow_explain_ui_experience` |
| Admin / meta | `servicenow_get_status`, `servicenow_list_instances`, `servicenow_use_instance`, `servicenow_test_connection`, `servicenow_check_capabilities`, `servicenow_find_tools`, `servicenow_list_packages`, `servicenow_enable_package`, `servicenow_disable_package`, `servicenow_explain_policy` |

### 2.3 REST endpoints and query params

All requests go through one primitive `snRequest()` in `src/core/http.ts`:
`https://{host}{path}?{params}` — the host is resolved and SSRF-checked first; the query string is
omitted from error messages.

Table API params (from `queryPage()` in `src/api/table.ts`):
`sysparm_query`, `sysparm_fields` (comma-joined), `sysparm_limit`, `sysparm_offset`,
`sysparm_display_value` (`"true"|"false"|"all"`), `sysparm_exclude_reference_link=true`,
`sysparm_view`, `sysparm_query_category`, `sysparm_no_count=true`, `sysparm_query_no_domain=true`,
`sysparm_suppress_pagination_header=true`.

| Capability | Method + path | Notes |
|---|---|---|
| Table read/write | `GET/POST/PATCH/DELETE /api/now/table/{table}` and `/api/now/table/{table}/{sysId}` | `PATCH` for update, `POST` for create |
| Aggregate | `GET /api/now/stats/{table}` | `src/api/aggregate.ts` |
| Batch | `POST /api/now/v1/batch` | `src/api/batch.ts` |
| Attachments | `POST /api/now/attachment`, `GET /api/now/attachment/{sysId}`, `GET /api/now/attachment/{sysId}/file`, `POST /api/now/attachment/file` | |
| Import set | `POST /api/now/import/{stagingTable}`, `/api/now/import/{stagingTable}/{sysId}` | |
| Knowledge | `GET/POST /api/sn_km_api/knowledge` | public Knowledge plugin API (`src/api/knowledge.ts`) |
| Catalog | `GET/POST /api/sn_sc/servicecatalog` | |
| Change | `GET/POST /api/sn_chg_rest/change` | Change Management plugin API |
| CMDB | `GET /api/now/cmdb/instance`, `/api/now/cmdb/instance/{class}`, `GET /api/now/cmdb/meta`, `/api/now/cmdb/meta/{class}`, `POST /api/now/identifyreconcile`, `/api/now/identifyreconcile/query` | IRE (Identification & Reconciliation) |
| Email | `GET/POST /api/now/email`, `GET /api/now/email/{sysId}` | |
| Code search | `POST /api/sn_codesearch/code_search/search` | |
| ATF run | `POST /api/sn_cicd/testsuite/run` with param `sys_id` (suite) or `test_sys_id` (single test); progress `GET /api/sn_cicd/progress/{executionId}` | final statuses 2=Successful, 3=Failed, 4=Canceled |
| Instance scan | `POST /api/sn_cicd/instance_scan` | |
| Update set (CI/CD) | `POST /api/sn_cicd/update_set/{preview|commit}/{sysId}` | |
| Remote update set | `/api/now/table/sys_remote_update_set/{sysId}` | |
| User preference | `GET/POST/PATCH/DELETE /api/now/table/sys_user_preference` | `PREF_PATH = "/api/now/table/sys_user_preference"` |

Tables per area: incident→`incident`; change→`change_request` + `conflict`; CMDB→`cmdb_ci`;
catalog→`sc_request`; attachments→`sys_attachment`; knowledge→`kb_knowledge`; users→`sys_user`,
`sys_user_group`, `sys_user_grmember`, `sys_user_has_role`; properties→`sys_properties`;
ops→`syslog`, `sys_trigger`, `sys_email`, `sys_semaphore`, `sys_outbound_http_log`,
`syslog_transaction`, `ecc_agent`, `ecc_queue`; ATF→`sys_atf_test_suite`, `sys_atf_test`;
flows→`sys_hub_flow`, `sys_flow_context`, `sys_hub_action_input`, `sys_hub_flow_input`;
update sets→`sys_update_set`, `sys_update_xml`, `sys_remote_update_set`.

### 2.4 Tool-package / role-based subsetting

Two layers:

1. **Static package manifest** (`src/mcp/registry.ts`): `PACKAGES: PackageSpec[]` — one object per
   package holding its tools plus optional MCP resources. 28 packages:
   `table, schema, aggregate, attachment, importset, batch, catalog, change, knowledge, cmdb,
   scripts, flows, codecheck, docs, instance, email, atf, revert, artifacts, updatesets, cicd,
   access, ops, history, properties, directory, ui, admin`. `admin` is always on. Load-time
   invariants: a tool's `package:` tag must match the manifest entry, and `ALL_PACKAGES`
   (`src/mcp/package-policy.ts`) must equal the manifest order.
2. **Dynamic per-session packages** (`src/mcp/packages.ts`): every policy-permitted tool is
   registered up front; tools of a disabled package are disabled through the SDK `RegisteredTool`
   handle, so `tools/list` shows exactly the configured surface. Toggling emits
   `notifications/tools/list_changed` (debounced). Tools: `servicenow_list_packages`,
   `servicenow_enable_package`, `servicenow_disable_package`.

Env: `SN_TOOL_PACKAGES` (requested set), `SN_PACKAGES_DENY` (never registrable, re-checked at enable
time → `PACKAGE_DENIED`), `SN_PACKAGES_READONLY` (write tools of the package not registered).
Named profiles: `discovery` (default: table+schema+aggregate), `core` (discovery+attachment),
`all`/`admin` (everything), `reader`, `developer` (reader+scripts+flows+codecheck+docs).

### 2.5 Impact analysis — `servicenow_where_used` + structural pass

Entry point `whereUsed(kind, name, opts)` in `src/api/whereused.ts`, kinds `table | field | script`.

- **Textual pass**: `searchCode({text, limit: 200, maxHits: 5})` → `/api/sn_codesearch/code_search/search`.
- **Attached automation** (kind = `table` only): `tableLogic(name)` groups →
  `business_rule`, `client_script`, `ui_policy`, `ui_action`, `acl`, each tagged
  `relation: "attached_to"` (vs `"references"` for textual hits).
- **Structural pass** (`src/api/references.ts`, `REFERENCE_SOURCES`, read in order):
  `dictionary_reference` → `sys_dictionary`; `list_layout` → `sys_ui_list`;
  `list_element` → `sys_ui_list_element`; `form_section` → `sys_ui_section`;
  `form_element` → `sys_ui_element`; `catalog_variable` → `item_option_new`;
  `flow_action_input` → `sys_hub_action_input`; `flow_input` → `sys_hub_flow_input`;
  `report` → `sys_report`; `pa_indicator_source` → `pa_cubes`; `uib_macroponent` →
  `sys_ux_macroponent`; `uib_client_script` → `sys_ux_client_script`.
  Per-source cap `STRUCTURAL_SOURCE_LIMIT = 100` → source marked `truncated`.
  Element queries use `element={e}^ORelementSTARTSWITH{e}.`.
- **Output**: `{kind, name, count, byType, references[], caveats[], structural?, mermaid?}` plus
  `mermaidTruncated` when `SN_DIAGRAM_MAX_NODES` is hit.

**Flow tracing** — `servicenow_trace_table_event` (`src/api/flows.ts` + `flows-model.ts`):
simulates the ordered chain for a table+operation without executing. Operations
`insert|update|delete|query` map to `sys_script` columns via
`OPERATION_FIELD = {insert:"action_insert", update:"action_update", delete:"action_delete", query:"action_query"}`.
Business rules query: `collectionIN{chain,global}^active=true^when={phase}^{OPERATION_FIELD}=true^ORDERBYorder`.
Chain resolved through `getTableChain` (parent-table inheritance) plus `global`. Lanes
(`TRACE_LANES`, opt-in): `transform_map, scheduled_job, client, data_policy, sla, event_script`.

### 2.6 Journal-based undo / revert

`src/core/write-journal.ts` (schema v2) + `src/api/revert.ts` + `src/tools/revert.ts`.

- **Storage**: `<docs>/<profile>/write-journal.jsonl`, chain head in `write-journal.head`,
  Markdown mirror `write-journal.md` (re-rendered from the latest 200 entries; JSONL rotated at
  `SN_JOURNAL_MAX_BYTES`, chain continued across files).
- **Line format** (JSONL, one per applied write): `schema_version: 2`, ULID `id`, `ts`, `profile`,
  `action` (`create|update|delete|execute|local_write|config`), `table`, `sys_id`, `fields`, `before`,
  `result` (`applied|failed|refused`), `error`, `plan_token`, `update_set`, `client`, `subject`,
  `batch_id`, `artifact_write`, `method`, `body_sha256`, `target`, `bytes`, `sha256`, `keys`, `tool`,
  `after_mod_count`, `reverts`, `force`, `cap_hit`, `prev` (sha256 of previous line).
  Values in `fields`/`before`/`error` go through the same redaction as tool results.
- **Revert** (`servicenow_revert_write`, input `entry_id`, `force`, `apply`):
  inverse map `create→delete`, `update→update`, `delete→create`. Drift check compares the record's
  current `sys_mod_count` against `after_mod_count`; refuses with `STALE_RECORD` (409) unless
  `force:true`. Revert itself is journaled with `reverts: <entry id>` and `tool: "servicenow_revert_write"`.
- **Revertible tools** (`REVERTIBLE_TOOLS`): `servicenow_create_record`, `servicenow_update_record`,
  `servicenow_upsert_record`, `servicenow_delete_record`, `servicenow_create_change`,
  `servicenow_update_change`, `servicenow_update_ci`, `servicenow_set_property`,
  `servicenow_upsert_artifact`, `servicenow_revert_write`.
- **Explicitly non-revertible** (`NOT_REVERTIBLE_TOOLS`, error code `NOT_REVERTIBLE`):
  `servicenow_create_ci` (IRE may have matched an existing CI), `servicenow_upload_attachment`,
  `servicenow_delete_attachment`, `servicenow_send_email`, `servicenow_insert_import_set_row`,
  `servicenow_order_catalog_item`, `servicenow_identify_reconcile`, `servicenow_batch`.
  System fields stripped on re-create: `sys_created_by, sys_created_on, sys_updated_by, sys_updated_on,
  sys_mod_count, sys_tags`.
- **Local Markdown knowledge base** (`src/api/docs.ts` + `docs-inspect.ts` + `docs-frontmatter.ts`
  + `docs-paths.ts` + `docs-manifest.ts`): root `SN_DOCS_DIR` (default `docs/instance/`), per-profile
  subfolder. Tools `servicenow_list_docs`, `servicenow_read_doc`, `servicenow_search_docs`,
  `servicenow_write_doc`. Writes carry frontmatter (`sn_generated`, `sn_generator`,
  `sn_generator_version`, `sn_profile`, `sn_instance`, `sn_generated_at`, `sn_source_hash`);
  text between `<!-- sn:manual:start -->` and `<!-- sn:manual:end -->` survives regeneration byte for
  byte. A generated doc is refused without `overwrite:true` → error code `DOC_GENERATED`. Every write
  rebuilds `index.json` (manifest) and `index.md`. The store's own `index.md`/`index.json` and the
  write journal cannot be written through it (path-traversal / audit-laundering guards;
  `assertRealPathInside`). Search is a literal substring scan returning `{path, line, snippet, heading}`,
  capped by `SN_DOCS_SEARCH_MAX`; files over `SN_DOCS_MAX_FILE_BYTES` are listed in `skipped`.

### 2.7 Update-set binding (`SN_UPDATE_SET`)

`src/api/updatesets.ts`. This is where `SN_UPDATE_SET` lives.

- **Resolution** (`planUpdateSetBinding(table, ref?)`): the per-call `update_set` argument wins,
  else `SN_UPDATE_SET` for the active profile (`getUpdateSetSetting(activeProfile())`). Undefined
  when neither is set — **no extra request is made**. Returns `{set, source: "argument"|"SN_UPDATE_SET",
  captured}`.
- **Capture check** (`isCaptured(table)`): a table extends `sys_metadata` → captured; otherwise
  `sys_dictionary` query `nameIN{chain}^internal_type=collection^attributesLIKEupdate_synch=true`.
  Data-row tables (task, cmdb, user data) are `captured:false` and the write runs **without**
  switching the update set.
- **How it wraps a Table API write** (`applyInUpdateSet(binding, run)`):
  1. `set.state !== "in progress"` → refuse, HTTP 409, code `UPDATE_SET_NOT_IN_PROGRESS`.
  2. Under a per-`instance|user` lock (`withLock`), set the caller's `sys_user_preference` row
     `name=sys_update_set` → `value = set.sys_id` (PATCH if the row exists, POST if not).
  3. If the set has an `application`, also set `updateSetForScope{application}` (global capture).
  4. Run the write with the journal field `update_set: set.sys_id` added.
  5. In a `finally`, restore the previous preferences in reverse (PATCH back the old value, or DELETE
     the created row) using a **fresh** AbortSignal so a cancelled call still restores. A failed
     restore is reported as `warning`, never as the write's failure.
  6. Report: `{update_set: {sys_id, name, bound: true, previous, restored, warning?}}`.
- **Plan preview** (`bindingPlanDetail`) states the source, the captured flag, and sets
  `would_refuse: true` when the set is not in progress.
- Applied in `src/tools/table.ts` (`servicenow_create_record`, `servicenow_update_record`,
  `servicenow_upsert_record`, `servicenow_delete_record`) and `src/api/upsert-artifact.ts`.

### 2.8 Safety controls

- **Table policy** (`src/core/policy.ts`): `SN_TABLES_ALLOW` (allowlist), `SN_TABLES_DENY`
  (denylist, always wins), `SN_READONLY` (global read-only). Per-profile overrides
  `SN_PROFILE_<NAME>_READONLY` / `_TABLES_ALLOW` / `_TABLES_DENY`.
- **Single evaluator** `evaluateTable(table, action)` with ordered rules, first match wins:
  `deny-exact → allow-exact → deny-pattern → protected-default → protected-confirm →
  import-set-allowlist → allow-pattern → not-in-allowlist → no-policy`. Globs `*`/`?` supported
  (`globToRegExp`).
- **Protected tables** (`PROTECTED_TABLES`): `sys_user`, `sys_user_has_role`, `sys_user_role`,
  `sys_user_grmember`, `sys_group_has_role`, `sys_user_role_contains`, `sys_security_acl`,
  `sys_security_acl_role`, `sys_properties`, `oauth_entity`, `sys_auth_profile_basic`, `sys_script`,
  `sys_ws_operation`, `sys_public`, `sys_ldap*`, `sys_certificate`, `sys_data_source`,
  `sys_rest_message*`. Mode `SN_PROTECTED_TABLES_WRITE` ∈ `confirm` (3.0 default) | `deny` | `allow`.
  Under `confirm`, an apply to a protected table requires the *call itself* to pass `apply: true`
  (`currentCall()?.explicitApply`) — `SN_WRITE_MODE=apply` alone is not consent.
- **Import-set staging tables**: `SN_IMPORT_SET_TABLES`, default `["u_*","imp_*"]`; `*` lifts it.
- **Package axes**: `SN_PACKAGES_DENY`, `SN_PACKAGES_READONLY`; enforced on the Batch API too
  (`assertPackageAllowed`, `assertPackageWriteAllowed`).
- **Plan/apply model**: writes are plan-by-default — `shouldApply(apply)` = `getWriteMode()=="apply"
  || apply===true`; otherwise a non-mutating `planPreview` is returned. Destructive applies under
  `SN_DESTRUCTIVE_CONFIRM=token|elicit` must return the single-use `plan_token` (opaque 28-char
  lowercase id, `PLAN_TOKEN_MAX=500`, TTL `SN_PLAN_TOKEN_TTL_SEC`).
- **Result-size guards**: `SN_MAX_RECORDS` cap on `fetchAll` (with a keyset `sys_id` cursor when no
  caller ORDERBY), `SN_MAX_RESULT_CHARS`, `SN_OVERSIZE_TO_FILE`, `SN_MAX_UPLOAD_BYTES`,
  `SN_MAX_BODY_BYTES`, `SN_MAX_WRITES_PER_SESSION`, `SN_MAX_DELETES_PER_SESSION`,
  `SN_MAX_BATCH_WRITES`, `SN_BATCH_MAX_REQUESTS`.
- **SSRF guard** (`src/core/host.ts`): `isBlockedHost` blocks `localhost`, `*.localhost`, `*.local`,
  `*.internal`, and private/loopback/link-local IPv4 (`0/8`, `127/8`, `10/8`, `192.168/16`,
  `172.16-31/12`, `169.254/16`) plus IPv6 equivalents (`::`, `::1`, `fe80::/10`, `fc00::/7`,
  IPv4-mapped forms). Default policy allows only `*.service-now.com`; `SN_ALLOWED_HOSTS` /
  `SN_HTTP_ALLOWED_HOSTS` widen it (entries may carry a port or a bracketed IPv6 literal).
- **Retry/timeout** (`src/core/http-retry.ts`): retry on `429` for any method; `502/503/504` only
  for idempotent (GET). Backoff `min(500*2^(attempt-1), 8000) + random(0..250)` ms. `Retry-After`
  honoured but capped by `SN_RETRY_AFTER_MAX_MS` (default 60 s). `SN_MAX_RETRIES`, `SN_TIMEOUT_MS`,
  `SN_DEADLINE_MS`. Per-host concurrency semaphore + circuit breaker (`SN_MAX_CONCURRENT`,
  `SN_MAX_QUEUE`, `SN_QUEUE_TIMEOUT_MS`, `SN_BREAKER_THRESHOLD`, `SN_BREAKER_RESET_MS`).
- **Other**: `SN_REDACT_PII`, `SN_REDACT_FIELDS`, `SN_ENV`=prod blocks ATF runs and (with
  `SN_PROD_WRITES`) writes; `SN_UPLOAD_MIME_ALLOW`; `SN_EMAIL_ALLOWED_DOMAINS`; `SN_CSV_FORMULA_GUARD`.
- 130 distinct `SN_*` env vars are referenced in `src/`.

### 2.9 Test tooling & coverage

- **node:test** (`node --test "test/**/*.test.js"`) + **c8** for coverage (`npm run test:coverage`).
- `.c8rc.json` **ratchet**: `{"check-coverage": true, "lines": 94, "branches": 82, "functions": 97,
  "reporter": ["text-summary","lcov"]}` — CI fails below these.
- **225 test files** in `test/`, incl. `test/write-journal.test.js`, `test/journal-v2.test.js`,
  `test/revert.test.js`, `test/whereused.test.js`, `test/updatesets.test.js`, `test/policy.test.js`,
  `test/http-retry.test.js`, `test/outbound-hardening.test.js`, `test/result-cap.test.js`,
  `test/response-size.test.js`, `test/protocol-packages.test.js`, `test/dynamic-packages.test.js`,
  `test/sdk-drift.test.js`, `test/live/live-smoke.test.js`.
- **Eval harness** beyond unit tests: `evals/` with 9 skill suites (`sn-discover`, `sn-drift`,
  `sn-impact`, `sn-safe-write`, `sn-security`, `sn-triage`, `sn-uib`, `sn-upgrade`) each with
  trigger/negative cases, graders and recorded ServiceNow mocks; plus `evals/tool-selection/` with
  `cases.json`, `description-hashes.json` and a token-budget fixture.
- CI (`.github/workflows/ci.yml`): Node 22/24/26 on ubuntu + macOS/22 leg, `permissions: contents: read`,
  runs lint → format:check → build → `test:coverage` (ratchet gates every leg) → `pack:check` →
  `mcpb:pack` → tracked-env-file guard → Prettier idempotency → Codecov upload (non-blocking) →
  `npm audit --omit=dev --audit-level=high`. Extra workflows: `codeql.yml`, `live-smoke.yml`,
  `sdk-drift.yml`, `skill-evals.yml`.
- `npm run check` = build + eval:mocks:check + lint + format:check + docs/env --check +
  docs/sync --check + roadmap/sync --check + docs/instructions --check + scan:surface +
  mcpb:manifest --check + test:coverage + pack:check + npm audit.

---

## 3. `seemsindie/servicenow-mcp-server`

### 3.1 Namespace / prefix convention

**Uniform `sn_` prefix** on every tool: `sn_<verb>_<noun>`. Tool titles are auto-generated from the
name by `generateToolTitle()` (`sn_get_record` → "Get Record"), with an abbreviation set
`{ci, kb, api, ui, rest, cmdb, apis}` uppercased.

147 static `registerTool` calls, plus two templated registrars:
- `src/tools/agile.ts` → `sn_list_${plural}`, `sn_create_${singular}`, `sn_update_${singular}` over 4 tables
  (`rm_story`/`stories`, `rm_epic`/`epics`, `rm_scrum_task`/`scrum_tasks`, `pm_project`/`projects`) = 12 tools.
- `src/tools/platform-scripts.ts` → `sn_list_${prefix}s`, `sn_get_${prefix}`, `sn_create_${prefix}`,
  `sn_update_${prefix}`, `sn_delete_${prefix}` over 5 types (`business_rule`/`sys_script`,
  `client_script`/`sys_script_client`, `ui_policy`/`sys_ui_policy`, `ui_action`/`sys_ui_action`,
  `ui_script`/`sys_ui_script`) = 25 tools.

Effective total ≈ 176 (README: "All 27 modules (176 tools) + instance tools"), matching the
README's 176-tool claim.

### 3.2 Representative tool names by domain (verbatim)

| Domain | Tools (from `src/tools/<file>.ts`) |
|---|---|
| Generic tables (`tables.ts`) | `sn_query_table`, `sn_get_record`, `sn_create_record`, `sn_update_record`, `sn_delete_record` |
| Schema (`schema.ts`) | `sn_get_table_schema`, `sn_discover_table`, `sn_list_tables`, `sn_explain_field` |
| ITSM incidents | `sn_list_incidents`, `sn_create_incident`, `sn_update_incident`, `sn_add_incident_comment`, `sn_add_incident_work_notes`, `sn_resolve_incident`, `sn_close_incident` |
| Problems | `sn_list_problems`, `sn_get_problem`, `sn_create_problem`, `sn_update_problem`, `sn_add_problem_comment`, `sn_add_problem_work_notes`, `sn_close_problem` |
| Changes | `sn_list_change_requests`, `sn_get_change_request`, `sn_create_change_request`, `sn_update_change_request`, `sn_add_change_task`, `sn_submit_change_for_approval`, `sn_approve_change`, `sn_reject_change`, `sn_add_change_comment`, `sn_add_change_work_notes` |
| Requests / Req items | `sn_list_requests`, `sn_get_request`, `sn_list_request_items`, `sn_get_request_item`, `sn_update_request_item`, `sn_submit_catalog_request` |
| CMDB | `sn_list_ci`, `sn_get_ci`, `sn_create_ci`, `sn_list_ci_relationships`, `sn_create_ci_relationship` |
| Service Catalog | `sn_list_catalogs`, `sn_list_catalog_items`, `sn_get_catalog_item`, `sn_update_catalog_item`, `sn_list_catalog_categories`, `sn_create_catalog_category`, `sn_update_catalog_category`, `sn_move_catalog_items`, `sn_create_catalog_variable`, `sn_list_catalog_variables`, `sn_update_catalog_variable`, `sn_validate_catalog_item`, `sn_get_catalog_recommendations` |
| Knowledge | `sn_list_knowledge_bases`, `sn_create_knowledge_base`, `sn_create_kb_category`, `sn_list_articles`, `sn_get_article`, `sn_create_article`, `sn_update_article`, `sn_publish_article` |
| Flow Designer | `sn_list_flows`, `sn_get_flow`, `sn_create_flow`, `sn_list_flow_variables`, `sn_create_flow_variable`, `sn_list_flow_stages` |
| Workflows | `sn_list_workflows`, `sn_get_workflow`, `sn_create_workflow`, `sn_update_workflow`, `sn_delete_workflow`, `sn_create_workflow_full`, `sn_create_workflow_activity`, `sn_create_workflow_transition`, `sn_publish_workflow` |
| Platform scripting | `sn_list_script_includes`, `sn_get_script_include`, `sn_create_script_include`, `sn_update_script_include`, `sn_delete_script_include`; plus the 25 templated `sn_list_business_rules`/`sn_get_business_rule`/`sn_create_business_rule`/`sn_update_business_rule`/`sn_delete_business_rule` (and the same quintet for `client_script`, `ui_policy`, `ui_action`, `ui_script`) |
| Scripted REST | `sn_list_scripted_rest_apis`, `sn_get_scripted_rest_api`, `sn_create_scripted_rest_api`, `sn_update_scripted_rest_api`, `sn_create_rest_resource`, `sn_update_rest_resource`, `sn_delete_rest_resource` |
| Widgets / UI pages | `sn_list_widgets`, `sn_get_widget`, `sn_create_widget`, `sn_update_widget`, `sn_delete_widget`; `sn_list_ui_pages`, `sn_get_ui_page`, `sn_create_ui_page`, `sn_update_ui_page`, `sn_delete_ui_page` |
| Attachments | `sn_upload_attachment`, `sn_list_attachments`, `sn_get_attachment` |
| Directory / users | `sn_list_users`, `sn_get_user`, `sn_create_user`, `sn_update_user`, `sn_list_groups`, `sn_create_group`, `sn_update_group`, `sn_add_group_members`, `sn_remove_group_members` |
| Update sets | `sn_list_update_sets`, `sn_get_update_set`, `sn_create_update_set`, `sn_update_update_set`, `sn_set_current_update_set`, `sn_commit_update_set`, `sn_add_to_update_set`, `sn_move_to_update_set`, `sn_clone_update_set` |
| Agile | `sn_list_stories`, `sn_create_story`, `sn_update_story`, `sn_list_epics`, `sn_create_epic`, `sn_update_epic`, `sn_list_scrum_tasks`, `sn_create_scrum_task`, `sn_update_scrum_task`, `sn_list_projects`, `sn_create_project`, `sn_update_project` |
| Ops / aggregate | `sn_aggregate_table`; app scope: `sn_get_current_application`, `sn_set_application_scope`; background scripts: `sn_execute_background_script`, `sn_create_fix_script`; import sets: `sn_create_import_set`, `sn_run_transform`; batch: `sn_batch_create`, `sn_batch_update`, `sn_batch_delete`; search: `sn_natural_language_search`; script sync: `sn_sync_script_to_local`, `sn_sync_local_to_script`, `sn_watch_and_sync`; instances: `sn_list_instances`, `sn_instance_info` |

### 3.3 REST endpoints and query params

Client (`src/client/index.ts`) builds URLs as `${baseUrl}/api/now/table/{tableName}` and sets exactly:
`sysparm_query`, `sysparm_fields`, `sysparm_limit`, `sysparm_offset`, `sysparm_display_value`,
`sysparm_exclude_reference_link`, `sysparm_suppress_pagination_header`, `sysparm_query_no_domain`.
`SNQueryParams` in `src/client/types.ts` is the authoritative list.

| Capability | Method + path | Notes |
|---|---|---|
| Table read | `GET /api/now/table/{tableName}` | |
| Table read one | `GET /api/now/table/{tableName}/{sysId}` | |
| Table create | `POST /api/now/table/{tableName}` | |
| Table update | `PATCH /api/now/table/{tableName}/{sysId}` | |
| Table delete | `DELETE /api/now/table/{tableName}/{sysId}` | |
| Aggregate | `GET /api/now/stats/{table}` | `sysparm_count=true`, `sysparm_query`, `sysparm_group_by`, `sysparm_{count,sum,avg,min,max}_fields` (built as `sysparm_${stat_type.toLowerCase()}_fields`), `sysparm_having_count`, `sysparm_orderby` (`ASC`/`DESC` prefix), `sysparm_display_value=true` |
| Attachments | `POST /api/now/attachment/file`, `GET /api/now/attachment/{sys_id}/file` | |
| Catalog order | `POST /api/sn_sc/servicecatalog/items/{catalog_item_sys_id}/order_now` | |
| Import set | `POST /api/now/import/{staging_table}/insertMultiple` | |
| App scope | `GET/POST /api/now/ui/concoursepicker/application` | |
| Scripted REST | Table API on `sys_ws_definition`, `sys_ws_operation` | |
| Background script | Table API on `sys_trigger` | |

Aggregate API is the only non-Table-API read path besides attachments/catalog/import/app-scope.

Tables: incident→`incident`; change→`change_request`, `change_task`, `sysapproval_approver`;
problem→`problem`; request→`sc_request`, `sc_req_item`, `sc_item_option_mtom`; CMDB→`cmdb_ci`,
`cmdb_rel_ci`; catalog→`sc_catalog`, `sc_cat_item`, `sc_category`, `item_option_new`; knowledge→
`kb_knowledge_base`, `kb_category`, `kb_knowledge`; flows→`sys_hub_flow`, `sys_hub_flow_logic`,
`sys_hub_flow_stage`, `sys_hub_flow_variable`; workflows→`wf_workflow`, `wf_workflow_version`,
`wf_activity`, `wf_transition`, `wf_condition`; scripting→`sys_script`, `sys_script_include`,
`sys_script_client`, `sys_ui_policy`, `sys_ui_action`, `sys_ui_script`; portal→`sp_widget`,
`sys_ui_page`; attachments→`sys_attachment`; users→`sys_user`, `sys_user_group`, `sys_user_grmember`;
update sets→`sys_update_set`, `sys_update_xml`; agile→`rm_story`, `rm_epic`, `rm_scrum_task`,
`pm_project`; schema→`sys_dictionary`, `sys_db_object`, `sys_choice`, `sys_documentation`,
`sys_index`, `sys_data_policy2`, `sys_script`; app scope→`sys_scope`, `sys_user_preference`.

### 3.4 Tool-package / role-based subsetting

`src/packages/definitions.ts` — `TOOL_PACKAGES: Record<string, string[]>` mapping package name →
**module keys** (not tool names). `src/packages/index.ts` `getPackageToolFilter(packageName)`
returns `null` for `full` (load everything) or a `Set<string>` of module keys; an unknown package
logs a warning and falls back to `full`. `src/server.ts` `TOOL_MODULES` maps 27 module keys to
registrar functions and registers only the allowed ones. Instance-management tools
(`sn_list_instances`, `sn_instance_info`) and the 7 MCP resources are always registered.

10 packages: `full`, `service_desk`, `change_coordinator`, `catalog_builder`, `knowledge_author`,
`platform_developer`, `system_admin`, `agile`, `integration_developer`, `portal_developer`.
Every package includes the `tables` module (asserted by `tests/packages/packages.test.ts`).

### 3.5 Impact analysis, journal/undo, local KB

**None.** Repo S has:
- No impact-analysis / where-used tool. `sn_discover_table` and `sn_explain_field` describe a
  table/field but do not search for dependents.
- No write journal and no revert/undo. `sn_delete_record`'s own description says "This is
  permanent and cannot be undone."
- No local Markdown knowledge base. The closest is `sn_sync_script_to_local` /
  `sn_sync_local_to_script` / `sn_watch_and_sync` (`src/tools/script-sync.ts`) — a file round-trip for
  scripts only, not a searchable KB.

### 3.6 Update-set binding

No `SN_UPDATE_SET` and no write-wrapping. `sn_set_current_update_set` is misleadingly named: it
issues `PATCH /api/now/table/sys_update_set/{sys_id}` with `{ state: "in progress" }` — it does
**not** touch the `sys_user_preference` `sys_update_set` row, so it does not actually switch the
caller's current update set. `sn_commit_update_set` PATCHes `{ state: "complete" }`.
`sn_add_to_update_set` creates a `sys_update_xml` row; `sn_move_to_update_set` PATCHes
`sys_update_xml` rows with `{ update_set: target_update_set }`; `sn_clone_update_set` creates a new
`sys_update_set` and copies `sys_update_xml` rows.

### 3.7 Safety controls

- **Result-size guards**: every list tool's `limit` is `z.number().int().min(1).max(100).default(20)`;
  `offset` is `z.number().int().min(0).default(0)`. `sn_clone_update_set` reads up to
  `sysparm_limit: 2000` `sys_update_xml` rows; `sn_move_to_update_set` up to 1000; `sn_get_update_set`
  up to 500.
- **Retry/timeout**: `src/client/index.ts` uses `fetch` with an `AbortController` timeout
  (`Request timed out after {this.requestTimeoutMs}ms`). **No retry/backoff logic** and **no
  non-idempotent-write protection** — a failed POST is not replayed, but there is also no backoff.
- **SSRF guard**: **none**. The instance URL comes from the local JSON config and is used as-is.
- **Read/write separation**: none. Write tools are exposed in the same registry as reads with no
  `WRITE_ENABLED`-style flag, no allow/deny table list, and no global read-only mode.
- **Auth** (`src/auth/`): Basic and OAuth 2.0 with token refresh; per-instance in
  `config/servicenow-config.json`. OAuth refresh (`src/auth/oauth.ts`).
- **Per-call instance targeting**: every tool takes an optional `instance` param; `registry.resolve(instance)`
  picks the client.
- **Human-name resolution** (`src/utils/resolve.ts`): `resolveRecordIdentifier` /
  `resolveOptionalUser` / `resolveOptionalGroup` map names, record numbers, emails and 32-hex sys_ids
  to sys_ids. Record-number prefix map: `INC→incident`, `CHG→change_request`, `PRB→problem`,
  `RITM→sc_req_item`, `REQ→sc_request`, `KB→kb_knowledge`, `STRY→rm_story`, `SPTSK→sprint_task`,
  `CTASK→change_task`, `PTASK→problem_task`, `STASK→sc_task`, `WF→wf_workflow`.
- **Encoded-query builder** (`src/utils/query.ts`): `QueryBuilder` with `equals`, `notEquals`, `like`,
  `startsWith`, `endsWith`, `isIn`, `isEmpty`, `isNotEmpty`, `greaterThan`, `lessThan`, `and()` (`^`),
  `or()` (`^OR`), `orderBy`, `orderByDesc`; `joinQueries(...fragments)` joins with `^`.

### 3.8 MCP resources (7)

`servicenow://incidents`, `servicenow://users`, `servicenow://knowledge`, `servicenow://tables`,
`servicenow://tables/{table}`, `servicenow://schema/{table}`, `servicenow://incidents/{number}`
(`src/resources/index.ts`).

### 3.9 Test tooling & coverage

- **Bun's built-in test runner** (`bun:test`); `npm test` → `bun test`. No `bunfig.toml`, no
  coverage config, **no coverage gate**.
- 22 test files: `tests/auth/{basic,factory,oauth}.test.ts`, `tests/client/{client,errors,registry}.test.ts`,
  `tests/tools/{aggregation,attachments,batch,catalog,import-sets,incidents,instances,problems,requests,schema,search,tables}.test.ts`,
  `tests/utils/{logger,progress,query,resolve,table-metadata}.test.ts`, `tests/packages/packages.test.ts`,
  `tests/config.test.ts`, `tests/server.test.ts`, `tests/mocks/index.ts`.
- `bun run typecheck` → `tsc --noEmit`.
- No GitHub Actions workflow in the repo tree (no `.github/workflows/` listed).

---

## 4. Cross-repo comparison for the merged design

| | aartiq/NowAIKit | IvanBBaev/servicenow-mcp-ai | seemsindie/servicenow-mcp-server |
|---|---|---|---|
| Prefix | none (bare verbs) | `servicenow_` | `sn_` |
| Tool count | ~508 literals (README "500+") | 100 `defineTool` specs (README badge "tools-100") | 147 static + templated ≈ 176 (README "176") |
| Package mechanism | env `MCP_TOOL_PACKAGE` → literal tool-name allow-list; plus `MCP_TOOL_DISCOVERY=lean\|core` + `search_tools`/`run_tool` | `PACKAGES` manifest (28) + dynamic per-session enable/disable (`servicenow_enable_package`), env `SN_TOOL_PACKAGES`/`SN_PACKAGES_DENY`/`SN_PACKAGES_READONLY` | env `toolPackage` → module-key filter set (10 packages) |
| Impact analysis | 5 tools, LIKE-based, Table API only | `servicenow_where_used` (code search + 12 structural source tables) + `servicenow_trace_table_event` | none |
| Journal / undo | none | JSONL v2 + hash chain, `servicenow_revert_write`, drift check | none |
| Local Markdown KB | none (only local-sync artifacts) | `SN_DOCS_DIR` store, 4 tools, frontmatter + manual blocks | none (script-sync only) |
| `SN_UPDATE_SET` | **absent** | present — binds writes via `sys_user_preference` | **absent** |
| Table allow/deny | denylist + scope prefix only (`NOWAIKIT_TABLE_DENYLIST`, `NOWAIKIT_FIELD_DENYLIST`, `NOWAIKIT_WRITE_SCOPE_PREFIX`) | `SN_TABLES_ALLOW` / `SN_TABLES_DENY` / `SN_READONLY` + protected-table modes + import-set allowlist | **none** |
| Global read-only | via tier flags (`WRITE_ENABLED` etc.) | `SN_READONLY` | none |
| Result-size guard | `sysparm_limit` ≤ 1000, default 10; 50 MB fetch cap | `SN_MAX_RECORDS`, `SN_MAX_RESULT_CHARS`, `SN_MAX_WRITES_PER_SESSION`, etc. | `limit` ≤ 100, `offset` ≥ 0 |
| SSRF guard | host allowlist for the public docs fetch only | full host policy (`src/core/host.ts`), default `*.service-now.com` only | none |
| Retry/timeout | 3 retries, exponential backoff, no auto-retry of non-idempotent writes, 30 s timeout | 429 any-method / 502-504 GET-only, jittered backoff, `Retry-After` capped, per-host semaphore + circuit breaker | timeout only, no retry |
| Tests | Vitest 33 files, coverage configured but **not gated** in CI | node:test 225 files, **c8 ratchet** lines 94 / branches 82 / functions 97, + 9 skill eval suites | Bun test 22 files, **no coverage gate**, no CI workflow |

### Notable gaps worth designing around

- **Repo A's `sys_update_set` "tool" is not a tool** — the literal `'sys_update_set'` in
  `src/tools/updateset.ts` is a `sys_user_preference` row `name` value inside
  `createRecord('sys_user_preference', { name: 'sys_update_set', … })`, not a registered tool name.
  A naive name-scraper over repo A will produce a phantom 509th tool.
- **Repo S's `sn_set_current_update_set` does not switch the caller's update set** — it only PATCHes
  `sys_update_set.state`. Repo A's `switch_update_set` and repo I's `applyInUpdateSet` both write the
  `sys_user_preference` row `name=sys_update_set`, which is the mechanism that actually works.
- **Only repo I has an update-set *binding* for writes** — A requires an explicit
  `switch_update_set` call; S has no binding at all.
- **Repo A's impact analysis is LIKE/substring only** and explicitly documents false positives;
  repo I's is a two-layer search (textual code search + 12 structural config sources).
- **Repo I is the only one with a write journal and a revert path**, and the only one with a
  local Markdown knowledge base.
