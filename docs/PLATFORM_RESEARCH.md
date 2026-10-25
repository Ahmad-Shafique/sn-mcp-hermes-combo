# ServiceNow Platform Surfaces for a Consolidated MCP Server

**Research date:** 2026-10-24 · **Primary release docs used:** Brazil (the "latest" release family at time of research)
**Sources:** `docs.servicenow.com` (via the official FluidTopics content API at `www.servicenow.com/docs/api/...`), the official `ServiceNow/ServiceNowDocs` GitHub markdown mirror (branch `brazil`), `servicenow.github.io/sdk` (official ServiceNow SDK docs), and `www.servicenow.com/community` (ServiceNow-employee-authored articles only).

**Verification legend**
- ✅ **VERIFIED** — confirmed verbatim in an official ServiceNow doc. Citation URL given.
- ⚠️ **PARTIAL** — officially documented but the specific detail asked about is not stated in the doc.
- ❌ **UNVERIFIED** — could not confirm from any official source. Do not treat as fact.

---

## 0. Headline answer to the naming question

**"Service Graph Workspace" is a real, distinct ServiceNow product — it is NOT a conflation.**

It is a **CMDB-focused workspace UI** (the successor/successor-sibling of **CMDB Workspace**), shipped as the **CMDB Workspace** store app (`sn_cmdb_ws`) plus the **Service Graph Workspace - Content** store app (`sn_sgw_content`). It is a *third* thing, distinct from both (a) the Service Graph/CSDM data model and (b) ServiceNow Workspace / Workspace Builder (the no-code app builder).

Critically, ServiceNow has **since consolidated Service Graph Workspace back into CMDB Workspace**. The Brazil release docs for the SGW Governance view state verbatim:

> "Note: Service Graph Workspace has been consolidated into CMDB Workspace, you can switch to CMDB Workspace to access everything in one unified workspace."

And the SGW landing page: *"The Service Graph Workspace is an efficient, central, and modernized way for you to work. Use Service Graph Workspace to search and explore the CMDB, examine health and recent activities, and access insightful dashboards and tools to support tasks in your organization."*

**Three distinct concepts:**

| Concept | What it is | Docs |
|---|---|---|
| **Service Graph** / **CSDM** | The *data model* — a standardized enterprise service graph over CMDB CIs and relationships, organized into domains (Foundation, Ideation & Strategy, Design & Planning, Build & Integration, Service Delivery, Service Consumption, Manage Portfolio). | [CSDM landing](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/csdm-landing-page.html) · [CSDM data domains](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/csdm-conceptual-model.html) |
| **Service Graph Workspace** | A *workspace UI* for CMDB work (Explore/Search, Governance, Tasks, Insights, Lists, SGC/Ingestion views). **Now consolidated into CMDB Workspace.** | [Service Graph Workspace](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/sg-workspace.html) · [Set up SGW](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/setup-service-graph-workspace.html) |
| **ServiceNow Workspace** / **Workspace Builder** / **App Engine Studio (AES)** | The *no-code/low-code app builder*. AES is the product; **Workspace Builder** is the no-code workspace builder inside AES. Note: "ServiceNow Workspace" is also used informally to mean the Next Experience agent workspace shell. | [Workspace Builder landing](https://www.servicenow.com/docs/r/application-development/workspace-builder/workspace-builder-landing.html) · [AES overview](https://www.servicenow.com/docs/r/application-development/app-engine-studio/aes-overview.html) |

**Service Graph definition** (ServiceNow employee article, 2020): *"Service Graph is the next-generation system of record for digital products and services... Service Graph includes CMDB. It extends the notion of CMDB to include new data types that encompass the entire digital lifecycle of applications and services."* — https://www.servicenow.com/community/itom-articles/cmdb-and-service-graph/ta-p/2323477 ✅

**SGW is mutually exclusive with CMDB Workspace** — verified verbatim from the setup page: *"CMDB Workspace and Service Graph Workspace can't be active at the same time. You can use only one of those at any given time."* ✅
Roles required: `sn_cmdb_admin`, `sn_cmdb_editor`, `sn_cmdb_user`. Plugins: `com.snc.cmdb.csdm.activation` (recommended), `com.snc.cmdb.csdm`, `sn_cmdb_pg_templts`, `sn-cmdb-nlq-search` (all required, active by default). ✅

---

## 1. ServiceNow REST API surfaces — exact endpoints

**General rules** ✅ ([REST APIs](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_RESTAPI.html))
- Versioned form: `/api/now/{api_version}/...` (e.g. `v1`, `v2`). Unversioned `/api/now/...` = latest for your instance.
- Methods: `GET`, `DELETE`, `HEAD`, `PATCH`, `POST`, `PUT`.
- Headers: `Accept` and `Content-Type` (`application/json` | `application/xml`). POST/PUT/PATCH/DELETE require both.
- Auth: Basic, OAuth, session cookie, certificate-based. `X-http-method-override` header supported.
- Universal query params: `sysparm_limit` (default **10000**), `sysparm_offset` (default 0), `sysparm_fields`, `sysparm_query`, `sysparm_view` (`desktop|mobile|both`), `sysparm_input_display_value`, `sysparm_display_value`, `sysparm_exclude_reference_link`, `sysparm_no_count`, `sysparm_suppress_pagination_header`, `sysparm_query_category`, `sysparm_query_no_domain`.
- Encoded-query operators: `=`, `!=`, `LIKE`, `STARTSWITH`, `ENDSWITH`, `^` (AND), `^OR` (OR), `ORDERBY`, `ORDERBYDESC`.
- **Dot-walking supported** in `sysparm_query` and `sysparm_fields` — but **NOT** in the Import Set API. ✅
- Pagination: `Link` response header with `rel="next|prev|first|last"`, plus `X-Total-Count`.

### 1.1 Table API — `/api/now/table/{tableName}`
✅ [Table API](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_TableAPI.html)

| Method | Path |
|---|---|
| GET | `/api/now/table/{tableName}` |
| GET | `/api/now/table/{tableName}/{sys_id}` |
| POST | `/api/now/table/{tableName}` |
| PUT | `/api/now/table/{tableName}/{sys_id}` |
| PATCH | `/api/now/table/{tableName}/{sys_id}` |
| DELETE | `/api/now/table/{tableName}/{sys_id}` |

Key query params on GET collection: `sysparm_query`, `sysparm_fields`, `sysparm_limit`, `sysparm_offset`, `sysparm_display_value` (`true|false|all`), `sysparm_exclude_reference_link`, `sysparm_view`, `sysparm_no_count`, `sysparm_suppress_pagination_header`, `sysparm_query_category`, `sysparm_query_no_domain`, plus bare `name-value pairs` (mutually exclusive with `sysparm_query`; display values accepted, e.g. `&state=closed`).
Notes: `sysparm_query_no_domain` requires `admin` or the `query_no_domain_table_api` role. `POST/PUT/PATCH` cannot pass multiple records — only the first is processed. Cannot write to Database Views. Response shape: `{"result": [...]}`.

### 1.2 Aggregate API — `/api/now/stats/{tableName}`
✅ [Aggregate API](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_AggregateAPI.html)

`GET /api/now/stats/{tableName}` — aggregate functions: `avg`, `max`, `min`, `sum`.

Query params: `sysparm_<aggregate>_fields` (e.g. `sysparm_avg_fields=duration,priority`), `sysparm_count`, `sysparm_group_by` (comma-separated), `sysparm_having` (syntax `aggregate^field^operator^value`, e.g. `count^priority^>^3`), `sysparm_order_by` (field or aggregate, `^DESC` suffix), `sysparm_display_value`, `sysparm_query`, plus name-value pairs.
Response shape: `{"result": [{"stats": {"avg": {...}}, "groupby_fields": [{"value": "...", "field": "..."}]}]}`.

### 1.3 CMDB APIs — `/api/now/cmdb/*`
✅ [CMDB Instance API](https://www.servicenow.com/docs/r/api-reference/rest-apis/cmdb-instance-api.html) · [CMDB Meta API](https://www.servicenow.com/docs/r/api-reference/rest-apis/cmdb-meta-api.html) · [CMDB Data Ingestion API](https://www.servicenow.com/docs/r/api-reference/rest-apis/cmdb-ingest-api.html)

**CMDB Instance API** (requires `itil` role; one record at a time for writes):

| Method | Path |
|---|---|
| GET | `/api/now/cmdb/instance/{className}` |
| GET | `/api/now/cmdb/instance/{className}/{sys_id}` |
| POST | `/api/now/cmdb/instance/{className}` |
| PUT | `/api/now/cmdb/instance/{className}/{sys_id}` |
| PATCH | `/api/now/cmdb/instance/{className}/{sys_id}` |
| POST | `/api/now/cmdb/instance/{className}/{sys_id}/relation` |
| DELETE | `/api/now/cmdb/instance/{className}/{sys_id}/relation/{rel_sys_id}` |

`POST .../relation` body: `inbound_relations[]` and `outbound_relations[]`, each `{ "target": "<sys_id>", "type": "<sys_id>" }`, plus required `source` (must be a choice value of `discovery_source` on `cmdb_ci`). Relationship **type** sys_ids live in **CI Relationship Type `cmdb_rel_type`**; relation instances live in **CI Relationship `cmdb_rel_ci`**. Response echoes `inbound_relations`/`outbound_relations` with `sys_id` (documented as "Located in the CI Relationship [`cmdb_rel_ci`] table") and `target`/`type` objects.

**CMDB Meta API** — `GET /api/now/cmdb/meta/{className}` (requires `itil`). Response fields: `attributes[]` (each with `element`, `label`, `type`, `is_inherited`, `is_mandatory`, `is_read_only`, `default_value`, `max_length`, `is_display`), `children[]`, `parent`, `name`, `label`, `icon`, `icon_url`, `is_extendable`, `identification_rules`, `relationship_rules`.
> This is the endpoint to use for **schema introspection** — it is how you learn a CI class's fields and parent/child hierarchy without guessing.

**CMDB Data Ingestion API** — `POST /api/now/cmdb/ingest/{data_source_sys_id}`. Docs explicitly say to prefer **Import Set `insertMultiple`** over this for scalability.

### 1.4 Attachment API — `/api/now/attachment/*`
✅ [Attachment API](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_AttachmentAPI.html)

| Method | Path |
|---|---|
| GET | `/api/now/attachment` (query: `sysparm_limit` default 1000, `sysparm_offset`, `sysparm_query` — queries relative to **Attachments `sys_attachment`**) |
| GET | `/api/now/attachment/{sys_id}` |
| GET | `/api/now/attachment/{sys_id}/file` |
| GET | `/api/now/attachment/{sys_id}/attributes` |
| GET | `/api/now/attachment/{sys_id}/attributes/{attribute_key}` |
| POST | `/api/now/attachment/file` |
| POST | `/api/now/attachment/upload` |
| POST | `/api/now/attachment/{sys_id}/attributes` |
| PUT | `/api/now/attachment/{sys_id}/attributes/{attribute_key}` |
| PATCH | `/api/now/attachment/{sys_id}` |
| DELETE | `/api/now/attachment/{sys_id}` |
| DELETE | `/api/now/attachment/{sys_id}/attributes` |
| DELETE | `/api/now/attachment/{sys_id}/attributes/{attribute_key}` |

`POST /api/now/attachment/file` query params: `file_name` (required), `table_name` (required), `table_sys_id` (required), `creation_time`, `encryption_context`. Binary body must be the last part of the request. `Content-Type` header is mandatory (the file's MIME type).

### 1.5 Import Set API — `/api/now/import/*`
✅ [Import Set API](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_ImportSetAPI.html)

| Method | Path |
|---|---|
| GET | `/api/now/import/{stagingTableName}/{sys_id}` |
| POST | `/api/now/import/{stagingTableName}` |
| POST | `/api/now/import/{stagingTableName}/insertMultiple` |

`insertMultiple` query params: `multi_import_set_id` (sys_id in **Multi Import Sets `sys_multi_import_set`**), `run_after` (sys_id in **Import Sets `sys_import_set`**; async only). Body format: default `{"records":[{"<ColumnLabel>":"<value>", ...}]}` or "Data source file" format. Transformation is **async by default**; make it sync via a record in **REST Insert Multiples `sys_rest_insert_multiple`**. **No dot-walking.**

### 1.6 Batch API — `/api/now/{api_version}/batch`
✅ [Batch API](https://www.servicenow.com/docs/r/api-reference/rest-apis/batch-api.html)

`POST /api/now/{api_version}/batch`. Body: `batch_request_id`, `rest_requests[]` where each item is `{ "id": "<required>", "method": "<required>", "url": "<required relative path incl. query params>", "body": "<Base64>", "headers": [{"name","value"}], "exclude_response_headers": bool }`.
Limits: per request item **5 MB** (`glide.rest.batch.max.inputSize`, max 10 MB); per response item **10 MB** (`glide.rest.batch.max.outputSize`, overridable by header `X-BATCHREQUEST-MAX-OUTPUT-SIZE`); **30 s** transaction quota (`REST Batch API request timeout`); over-limit items come back in the `unserviced` array. `Accept: application/json` or `multipart/mixed`. Request `Content-Type` must be `application/json`.

### 1.7 GraphQL API — `/api/now/graphql`
✅ Endpoint path confirmed in official ServiceNow SDK docs: *"A query targets `POST /api/now/graphql` and wraps fields under `{ { { ... } } }`."* — https://servicenow.github.io/sdk/guides/graphql-api-guide
✅ [Query record data using the GraphQL API framework](https://www.servicenow.com/docs/r/api-reference/web-services/scripted-graph-ql.html)

- **Method:** `POST /api/now/graphql`.
- **Envelope:** two nested namespaces — application namespace (derived from app scope, camel-cased, e.g. scope `x_snc_my_app` → `xSncMyApp`) then schema namespace: `query { xSncMyApp { myApi { ... } } }`.
- **Config tables:** `sys_graphql_schema` (GraphQL Scripted Schemas; SDL in the `schema` field), plus GraphQL Scripted Resolvers / Typeresolvers / Resolver Mappings related lists. Resolver mapping table name: **`sys_graphql_resolver_mapping`** ✅ (one per path).
- **Namespace:** app namespace + schema namespace also prefix the runtime ACL paths, e.g. `/xSncMyApp/catalogGql/items/cost`.
- **ACL type:** `graphql`; schema-gate ACL for the whole API + field-level path ACLs.
- **Role for introspection:** `graphql_schema_admin`.
- **System properties** ✅: `glide.graphql.glide_record_schema.introspection_enabled` (default false), `glide.graphql.debug` (false), `glide.graphql.introspection_enabled` (false).
- **Unsupported:** Subscription operations; custom scalar types. Directives: `@source`, `@defer` (needs `Accept: multipart/mixed`).
- Resolver globals: `env.getArguments()`, `env.getSource()`; typeresolvers additionally `env.getObject()`, `env.getTypeName()`.

### 1.8 Scripted REST API (custom endpoints)
✅ [Scripted REST APIs](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_CustomWebServices.html)

- **URI format:** `https://<instance.service-now.com>/api/<name_space>/<version>/<api_id>/<relative_path>`
  - `<name_space>` = `glide.appcreator.company.code` value for global scope, or the scoped app scope name (e.g. `x_company_appname`).
  - `<version>` optional (e.g. `v1`); a default version may be marked.
  - `<api_id>` = the **API ID** field on the Scripted REST Service form (defaults from service name).
  - `<relative_path>` = resource path, e.g. `/{id}`.
- Roles to *manage*: `web_service_admin`. Roles are *not* required to *call* the endpoint.
- Schemas must be **OpenAPI 3.0.1**.
- Default formats: `application/json`, `application/xml`, `text/xml`.
- ACL `Type` must be **`REST_Endpoint`**.
- Config tables: Scripted REST Services (`sys_script_rest_service`), resources, and the newer **`sys_rest_message`/`sys_rest_message_fn`** family for outbound. ❌ The exact config-table name for Scripted REST Service is **UNVERIFIED** from the docs I could retrieve (the docs describe the form but name it "Scripted REST Service form" under **Scripted Web Services → Scripted REST APIs**).

### 1.9 Service Catalog API — `/api/sn_sc/servicecatalog/*`
✅ [Service Catalog API](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_ServiceCatalogAPI.html) — 24 endpoints. Note the base path is `/api/sn_sc/...`, **not** `/api/now/...`. Versioned form: `/api/sn_sc/{api_version}/servicecatalog/...`.

| Method | Path | Key query params |
|---|---|---|
| GET | `/api/sn_sc/servicecatalog/catalogs` | `sysparm_limit`, `sysparm_text`, `sysparm_view` |
| GET | `/api/sn_sc/servicecatalog/catalogs/{sys_id}` | `sysparm_view` |
| GET | `/api/sn_sc/servicecatalog/catalogs/{sys_id}/categories` | `sysparm_limit`, `sysparm_offset`, `sysparm_top_level_only`, `sysparm_view` |
| GET | `/api/sn_sc/servicecatalog/categories/{sys_id}` | `sysparm_view` |
| GET | `/api/sn_sc/servicecatalog/items` | `sysparm_catalog`, `sysparm_category`, `sysparm_limit`, `sysparm_offset`, `sysparm_text`, `sysparm_type`, `sysparm_view` |
| GET | `/api/sn_sc/servicecatalog/items/{sys_id}` | `sysparm_view` |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/add_to_cart` | |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/add_to_wishlist` | |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/order_now` | |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/submit_producer` | `sysparm_view` |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/checkout_guide` | |
| PUT | `/api/sn_sc/servicecatalog/items/{sys_id}/submit_guide` | |
| POST | `/api/sn_sc/servicecatalog/items/{sys_id}/get_invalid_delegated_users` | |
| GET | `/api/sn_sc/servicecatalog/items/{item_sys_id}/delegation/{user_sys_id}` | |
| GET | `/api/sn_sc/servicecatalog/cart` | |
| PUT | `/api/sn_sc/servicecatalog/cart/{cart_item_id}` | |
| DELETE | `/api/sn_sc/servicecatalog/cart/{cart_item_id}` | |
| DELETE | `/api/sn_sc/servicecatalog/cart/{sys_id}/empty` | |
| POST | `/api/sn_sc/servicecatalog/cart/checkout` | |
| POST | `/api/sn_sc/servicecatalog/cart/submit_order` | |
| GET | `/api/sn_sc/servicecatalog/cart/delivery_address/{user_id}` | |
| GET | `/api/sn_sc/servicecatalog/wishlist` | |
| GET | `/api/sn_sc/servicecatalog/wishlist/{cart_item_id}` | |
| POST | `/api/sn_sc/servicecatalog/variables/{sys_id}/display_value` | |

Related tables referenced: `sc_catalog`, `sc_category`, `sc_cat_item`, `sc_cat_item_producer`, `sc_cat_item_guide`, `sc_request`. ✅ (table names appear in the API doc)
There are also separate product APIs: **Service Catalog Open API**, **Product Catalog Open API**, **Product Catalog Search API** (in the REST API reference index). ✅

### 1.10 `sys_script` — executing server-side scripts
⚠️ **There is no documented public REST endpoint that executes arbitrary server-side script.** What *is* officially documented:

- `sys_script` is the **Business Rule** table. ✅ [Business Rule API](https://www.servicenow.com/docs/r/application-development/servicenow-sdk/business-rule-api-now-ts.html): *"The Business Rule API defines server-sides scripts [sys_script] that run when a record is displayed, inserted, updated, or deleted, or when a table is queried."*
- Business Rule properties (Fluent API): `name`, `table`, `script`, `order` (default 100), `active` (default true), `when` (`before|after|async|display`, default `before`), `action` (`insert|update|delete|query`), `addMessage`, `abortAction`.
- Because `sys_script` is a normal table, the **Table API** can read/write it: `GET/POST /api/now/table/sys_script`. ❌ The docs I retrieved do **not** state that creating a `sys_script` row via the Table API executes it — community threads assert this works, but **do not treat it as verified**. Access is ACL-restricted (admin-only by default).
- **The officially supported paths for running server-side code are:**
  1. **Scripted REST API** (§1.8) — you write the script on the form; clients just call the endpoint. ✅
  2. **ServiceNow SDK `now-sdk exec`** — *"runs a server-side script on the authenticated ServiceNow instance, the same way the platform's Scripts - Background page does."* Supports `--scope`, `--reason`, `--record-for-rollback` (default true), `--timeout` (default 300000 ms), `--output json|raw`, `--select`, `--server-logs`. ✅ https://servicenow.github.io/sdk/guides/exec-guide
  3. **GraphQL resolvers** — server-side JS with GlideRecord access (§1.7). ✅
  4. **Business Rules / Flow** — declarative triggers on `sys_script`, `sys_flow`, etc.
- **Flow Designer (Workflow Studio) API access** ✅ — [API access to Workflow Studio flows](https://www.servicenow.com/docs/r/build-workflows/workflow-studio/api-access-flow-designer.html):
  - Server: **`FlowAPI`** (`ScriptableFlowAPI`) — `executeActionQuick()`, `executeFlowQuick()`, `executeSubflowQuick()`, `startActionQuick()`, `startFlowQuick()`, `startSubflowQuick()` (quick methods always run as system user).
  - Client: **`GlideFlow`** — flows/subflows/actions must be marked **Client callable** at design time.
  - `sys_flow` / `sys_flow_definition` are the underlying tables. ⚠️ The exact field/table names for flow definitions are **UNVERIFIED** from the retrieved docs.

### 1.11 Other relevant verified APIs (from the REST API reference index)
✅ [REST API reference](https://www.servicenow.com/docs/r/api-reference/rest-apis/api-rest.html) — 130+ APIs. Notable for this project:
- **Identification and Reconciliation API** — `POST /api/now/identifyreconcile`, `POST /api/now/identifyreconcile/query` (simulate), `POST /api/now/identifyreconcile/enhanced` (Enhanced IRE). Requires `itil` or `asset`. Body `items[]` with `className`, `internal_id`, `lookup[]`, `related[]`, `settings{}`, `sys_object_source_info{}` (`source_feed`, `source_name`, `source_native_key`, `source_recency_timestamp`), `values{}`. Query param `sysparm_data_source` (choice value of `discovery_source` on `cmdb_ci`). ✅ [doc](https://www.servicenow.com/docs/r/api-reference/rest-apis/c_IdentifyReconcileAPI.html)
- **Metrics/Time Series API** (`/api/now/metrics/...`), **AI Assets API**, **Agent APIs**, **Knowledge API**, **cs-catalog API**, **sg_services API**, **CI Lifecycle Management API**, **Service Test Management API**, **Snapshot API**, **SQL API** (out-of-band read path), **Attachment CSM API**.

---

## 2. The CMDB / CSDM graph

### 2.1 Tables a client actually reads

| Table | Role | Verified? |
|---|---|---|
| `cmdb_ci` | Base CI table; holds basic attributes of all CIs. Descendants are IT CIs. | ✅ |
| `cmdb_ci_*` (e.g. `cmdb_ci_hardware`, `cmdb_ci_computer`, `cmdb_ci_server`, `cmdb_ci_database`, `cmdb_ci_appl`, `cmdb_ci_business_app`, `cmdb_ci_service`, `cmdb_ci_information_object`, `cmdb_ci_service_discovered`) | CI class tables | ✅ |
| `cmdb_rel_ci` | **CI Relationship** — the relationship-instance table. This is the traversal table. | ✅ |
| `cmdb_rel_type` | **CI Relationship Type** — holds relationship type sys_ids. | ✅ |
| `cmdb_class_info` | **CMDB Class Information** — class descriptions, plus (via CMDB CI Class Models app) class metadata. | ✅ |
| `cmdb_identifier` / `cmdb_identifier_entry` | Identification rules / entries | ✅ |
| `cmdb_key_value` | Key Value — CI tags | ✅ |
| `cmdb_group` | CMDB Groups | ✅ |
| `cmdb_data_management_task` | CMDB Data Management Task (certification tasks). Field `policy.cmdb_policy_type` = `Certification`. | ✅ |
| `cmdb_health_metric_pref` | CMDB Health metric preferences | ✅ |
| `cmdb_metadata_hosting` | Dependent relationships (CMDB CI Class Models app) | ✅ |
| `cmdb_duplicate_lookup_related_allowed_class` | De-dup lookup related allowed classes | ✅ |
| `cmdb_rel_source` (as `sys_rel_source`) | Relationship Sources — cascading records deleted when a non-dependent `cmdb_rel_ci` row is deleted. The docs render it as **Relationship Sources `[sys_rel_source]`**. | ✅ |
| `life_cycle_control` | Life-cycle stage definitions, aggregated up the class hierarchy | ✅ |
| `svc_ci_assoc` | Service↔CI associations (used by Change "Refresh Impacted Services") | ✅ |
| `spm_taxonomy_node` | Business/tech services ↔ `spm_service_portfolio` | ✅ |
| `sys_csdm_domain_model` | — | ❌ **UNVERIFIED** |
| `sys_csdm_context` | — | ❌ **UNVERIFIED** |

**Important correction on `sys_csdm_*`:** I searched the full official ServiceNowDocs corpus (8,773 markdown files across `servicenow-platform`, `api-reference`, `application-development`, `it-service-management`) and the official docs full-text search index for `sys_csdm_domain_model` and `sys_csdm_context`. **Neither name appears in any official ServiceNow documentation.** Semantic search returns the CSDM landing/conceptual-model pages for those strings but no page that names those tables. `cmdb_class_info` **is** documented (see above). **Treat `sys_csdm_domain_model` and `sys_csdm_context` as UNVERIFIED — likely internal/private tables not part of the public contract.** Verify against a live instance's `sys_db_object` before relying on them.

Similarly, **`cmdb_rel`** (without `_ci`) is **not** the CMDB relationship table. The official name is `cmdb_rel_ci`. There is no documented `cmdb_rel` table in the CMDB docs. ❌

### 2.2 How CSDM maps to physical tables
✅ [How CSDM concepts map to CMDB tables](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/csdm-to-cmdb-mapping.html)
- Business Application data belongs in `cmdb_ci_business_app`, **not** `cmdb_ci_app`.
- Business services and technology management services connect to `spm_service_portfolio` through `spm_taxonomy_node`.
- Life-cycle stage inheritance is **aggregation-based**: a child class's `life_cycle_control` definitions are *combined with* all parent classes' (children extend, they don't override). By contrast, `sys_choice` inheritance **overrides**.

✅ [CI relationships in the CSDM](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/ci-relationships.html)
- CSDM v5 uses **Uses::Used By** between Business Applications and Application Services (earlier versions: **Consumes::Consumed By**). Enterprise Architecture Workspace users should keep **Consumes::Consumed by** for correct TLM/TRM timelines.
- A Business Application relates ultimately to an Application Service table, not any other Service Instance type.

### 2.3 CSDM domains
✅ [CSDM data domains](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/csdm-conceptual-model.html): **Foundation**, **Ideation & Strategy**, **Design & Planning**, **Build & Integration**, **Service Delivery**, **Service Consumption**, **Manage Portfolio** (overlay).
Service types: **Technology Management Service** (provider-focused, single-level, leaf nodes in service hierarchies; used for impact analysis and approvals in Incident/Problem/Change), **Service Instances** (logical representations of deployed application stacks; per region/environment), **Business Services**.
Crawl-stage physical tables called out: `cmdb_ci_business_app`, `cmdb_ci_service_discovered`, `cmdb_ci_appl`. ✅ [Crawl stage](https://www.servicenow.com/docs/r/servicenow-platform/common-service-data-model-csdm/csdm-implement-crawl-stage.html)

### 2.4 Impact analysis — how it actually works

**Mechanism (Change Management)** ✅ [Associated CIs on a change request](https://www.servicenow.com/docs/r/it-service-management/change-management/c_AffectedCIsAndImpactedServices.html) · [Refresh impacted services and CIs](https://www.servicenow.com/docs/r/it-service-management/change-management/refresh-impacted-services-cis.html)
- Change requests carry two related lists: **Affected CIs** (manual) and **Impacted Services/CIs** (computed).
- The **Refresh Impacted Services** UI action populates Impacted Services/CIs. Sources, in order:
  1. `change.refresh_impacted.include_affected_cis` = true → services from the **`svc_ci_assoc`** table; false → services resolved via the **`CIUtils`** script include.
  2. `change.conflict.populateimpactedcis` = true → additional services from **`ChangeCollisionHelper`** (conflict detection).
  3. If the **Service Mapping** plugin is active → Application Services retrieved by association type **Runs On** where the association child is one of the affected CIs.
  4. Then Business Applications and Service Offerings are populated if their properties are enabled.
- The refresh runs on: conflict detection; automatically when the change moves out of `New`; or manually via the **Additional actions → Refresh Impacted Services** menu.
- `com.snc.task.refresh_impacted_services` property lists the task tables where the action is available (now beyond just `change_request`).
- `com.snc.task.principal_class_filter` controls the Principal Class filter on the Affected CIs list.

**Mechanism (ServiceNow's own AI impact analysis)** ✅ [CMDB impact analysis agentic workflow details](https://www.servicenow.com/docs/r/servicenow-platform/now-assist-for-configuration-management-database-cmdb/na-cmdb-awf-impact-analysis-ref.html)
- *"The workflow builds the dependency topology using a three-phase breadth-first search (BFS) through the CMDB relationship table (`cmdb_rel_ci`)."* — **explicit confirmation that `cmdb_rel_ci` is the traversal table.**
- Phases: Resolve inputs → Fetch topology → Invoke LLM.
- Output schema per impacted item: `sysId`, `ciName`, `ciClass`, `impactLevel` (`high|medium|low|none`), `impactType` (`availability|performance|data-integrity|functional|security|operational|none`), `confidence` (`high|medium|low`), `reason`.
- Tool `GetFullTopology` loads the topology visualization, processes it in chunks, sends each chunk to the LLM, and persists results.
- Requires `itil`; supports `change_request` and `incident` only. Change state 4 (Canceled) rejected; change state 5 (New) skips LLM summarization; incident state 8 (Closed) rejected. Needs exactly one affected CI if the record has no CI set.

**Dependency views** (UI, but the same graph) ✅ — CI relationship map reachable from a change request's Configuration Item field; "Add Affected CIs" from a highlighted dependent node.

### 2.5 What a client needs to traverse the service graph

1. **Schema first.** `GET /api/now/cmdb/meta/{className}` → learn `attributes[]`, `parent`, `children[]`, `relationship_rules`, `identification_rules`. This is the only *documented* class-introspection endpoint.
2. **CI reads.** `GET /api/now/table/{cmdb_ci_class}?sysparm_query=...` with `sysparm_fields` (dot-walking works), `sysparm_display_value=true`.
3. **Edges.** `GET /api/now/table/cmdb_rel_ci` — filter on the parent/child reference columns; use `cmdb_rel_type` to resolve the relationship type sys_id to a label. Relationship direction = parent → child.
4. **BFS/DFS** over `cmdb_rel_ci` yourself, exactly as ServiceNow's own impact-analysis workflow does. There is **no** documented REST endpoint that returns a transitive impact closure.
5. **Service associations.** `svc_ci_assoc` for service↔CI (Service Mapping); `cmdb_rel_ci` for CI↔CI.
6. **Service-level view.** `cmdb_ci_service` (business/technology services), `cmdb_ci_service_discovered` (mapped application services), `spm_service_portfolio` + `spm_taxonomy_node`.
7. **Business context.** `cmdb_ci_business_app`, `cmdb_ci_information_object`, `cmdb_ci_business_capability`.
8. **Queries.** `sysparm_query` operators `^`/`^OR`, `STARTSWITH`, `LIKE`, `ORDERBY`/`ORDERBYDESC`; and the **CMDB Query Builder** (UI) warns that for a relationship node you can only select `parent`, `child`, and `type` columns from `[cmdb_rel_ci]` — you cannot select other columns from it. ✅ [Build CMDB query](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/use-cmdb-query-builder.html)

---

## 3. What "ServiceNow Workspace" exposes to a client

**Product reality (Brazil release)** ✅
- The no-code/low-code app builder is **App Engine Studio (AES)**: *"a guided, low-code tool for developing rich web applications to store information, automate business processes, and solve business problems."* It bundles **Catalog Builder**, **Workflow Studio** (the current name for Flow Designer), **Workspace Builder**, **Mobile App Builder**, and **App Engine Management Center (AEMC)** for governance.
- **Workspace Builder** is the no-code workspace builder inside AES: *"Workspace Builder for App Engine is a streamlined, no-code environment that enables you to create a custom workspace from within App Engine Studio (AES) quickly and efficiently."* For workspaces built **starting with Brazil** you use Workspace Builder; for older ones or advanced config, use **UI Builder** from a tab in AES.
- A built workspace contains: **Home page, List page, Record page, Search page, Analytics Overview** (Analytics Q&A, Indicator Scorecard, Dashboards Overview).
- Scoped app model: scope name → `x_company_appname`; **Application scope** determines the scripted-REST namespace and the GraphQL application namespace.

**What a client can actually reach** ✅ — almost everything is plain table data:
- **Scoped app tables** — every custom table in a scoped app is a normal table: `GET /api/now/table/{scope_table}`. AES apps expose their own tables; the workspace itself is UI, not data.
- **Records in workspace tables** — the "workspace" is a configuration over platform tables. Records live in standard tables (`incident`, `task`, `sc_req_item`, `case`, `cmdb_ci_*`) and are surfaced through the workspace's list/record pages. Config table referenced in docs: **Platform table UX List Menu Configuration `sys_ux_list_config`** (used by CMDB Workspace to build its default lists) ✅.
- **Workspace Builder / UI Builder** — page/layout configuration, stored as metadata records. ⚠️ Exact table names for workspace page configuration are **UNVERIFIED**.
- **Flow Designer (Workflow Studio)** — flows/subflows/actions, exposed server-side via `FlowAPI` and client-side via `GlideFlow`; **Client callable** opt-in per element. ✅
- **Automation** — Flow Designer, business rules on `sys_script`, catalog workflows on `sys_workflow`. ✅
- **Record pages / related lists** — driven by the platform's form/related-list model, so `sys_related_list` / `sys_related_list_field` apply. ⚠️ Table names **UNVERIFIED** from retrieved docs.

**CMDB Workspace / SGW client-visible tables** ✅ [Components installed with CMDB Workspace](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/installed-with-cmdb-workspace.html) (plugin `sn_cmdb_ws`):
`sn_cmdb_ws_group_metadata`, `sn_cmdb_ws_group_query_metadata`, `sn_cmdb_ws_nlq_sample_search`, `sn_cmdb_ws_nlq_sample_search_table`, `sn_cmdb_ws_nlq_excluded_table`, `sn_cmdb_ws_imp_action_card_config`, `sn_cmdb_ws_quick_links`, `sn_cmdb_ws_ms_cis_by_number_of_sources`, `sn_cmdb_ws_ms_cis_with_single_source`, `sn_cmdb_ws_ms_class_metadata`, `sn_cmdb_ws_ms_data_mismatch`, `sn_cmdb_ws_ms_data_mismatch_config`, `sn_cmdb_ws_ms_discovery_sources_not_reporting`, `sn_cmdb_ws_ms_settings_weight_type`.

**SGW default lists** (source tables exposed to users) ✅ — CMDB Groups `cmdb_group`; CI Identifier `cmdb_identifier`; Relationships `cmdb_rel_ci`; Tags `cmdb_key_value`; plus `dscy_swtch_fwd_rule`, `dscy_swtch_partition`, `cmdb_switch_port`, `dscy_switchport`, `cmdb_tcp`.

**SGW views** ✅ — Explore and Search, Governance, Tasks, Insights, Lists, SGC (Ingestion) Central, Data Owner, Create-a-custom-list. Insights dashboards: CMDB Health, CMDB Data Foundation, CSDM Data Foundation, CMDB success advisor, Feature adoption, Performance insights, Cloud vs Non-cloud, Service instances, CMDB 360.
Search modes: **AI Search** (ServiceNow Otto for CMDB v3.0+, `nowassistpaneluser` role), **Intelligent Search / NLQ** (`sn-cmdb-nlq-search` plugin), **Conditional Search**. Exploration modes: **Contexts** (requires Service Graph Workspace - Content store app + Data Model Navigator) and **Classes** (fallback).

---

## 4. Officially published ServiceNow MCP surfaces — **YES, they exist**

This is the most important finding for the parent's design decision: **ServiceNow ships official MCP servers.** Building a *generic* MCP server over ServiceNow's REST APIs is a valid but partially redundant strategy.

### 4.1 MCP Server Console (the platform product)
✅ [MCP Server Console](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-platform-manager-landing.html) · [Exploring MCP Server Console](https://www.servicenow.com/docs/r/intelligent-experiences/exploring-mcp-server-console.html)

- **Purpose:** *"create MCP servers on an instance and configure the tools that they expose or use a preconfigured Quickstart Server."*
- **Server URL format:** `https://<instance>.service-now.com/sncapps/mcp-server/mcp/<server-name>` ✅
  - Quickstart Server: `https://<instance>.service-now.com/sncapps/mcp-server/mcp/sn_mcp_server_default`
  - Base URL `/sncapps/mcp-server`, Scope `mcp_server`.
- **Auth:** OAuth 2.0. `https://<instance>.service-now.com/oauth_auth.do`, `oauth_token.do`, `oauth_revoke.do`, callback `https://<instance>.service-now.com/oauth/callback`. AI Agent Studio path supports OAuth **2.1** with Dynamic Client Registration.
- **Transport:** Streamable HTTP. Stdio **not** supported. MCP resources and prompts **not** supported. Only stateless/remote servers.
- **Payload limits:** request > **26 KB** → error; response > **64 KB** → error (Brazil patch 1, Australia patch 7, Zurich patch 13).
- **Roles:** `sn_mcp_server.admin` (contains `sn_mcp_server.tools_admin`), `sn_mcp_server.tools_admin`, `sn_mcp_server.viewer`.
- **Tables:** ✅ [Components installed with MCP Server Console](https://www.servicenow.com/docs/r/intelligent-experiences/installed-mcp-server-console.html) — `sn_mcp_ai_skill_tool_definition`, `sn_mcp_ai_skill_tool_input`, `sn_mcp_server_registry`, `sn_mcp_scripted_rest_tool_definition`, `sn_mcp_scripted_rest_input`, `sn_mcp_tool_definition`, `sn_mcp_tool_input`.
- **Tool categories** ✅ — Subflows, Actions, Knowledge Graph schemas, **REST APIs**, AI skills (incl. custom via AI Skill Kit), **Playbooks**.
- **Built-in tools** ✅ [MCP Server Console tools](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-server-tools.html): `case_summarization` (AI Skill), `email_recommendation` (AI Skill), `incident_summarization` (AI Skill), `lookup_case_records` (Scripted REST API), `lookup_incident_records` (Scripted REST API), `lookup_kb_records` (Scripted REST API).

### 4.2 ITSM MCP Server (official, first-party tool names)
✅ [ITSM MCP Server](https://www.servicenow.com/docs/r/it-service-management/itsm-mcp-server-overview.html) · [tools reference](https://www.servicenow.com/docs/r/it-service-management/itsm-mcp-server-tools-reference.html) · [setup](https://www.servicenow.com/docs/r/it-service-management/set-up-itsm-mcp-server.html)

Plugins required: `sn_itsm_gen_ai` (ServiceNow Otto for ITSM), `sn_mcp_server`, `sn_itsm_mcp_server`. Base role to call tools: **`sn_mcp_server.viewer`**. OAuth client entry created on activation, e.g. `sn_itsm_mcp_server.itsm_default`. Auth scope option `a2aauthscope` enables REST A2A access to the AI Agent MCP tools.

**Verbatim tool names:**

*Incident management:*
- `sn_itsm_mcp_server.incident.get_details`
- `sn_itsm_mcp_server.incident.modify`
- `sn_itsm_mcp_server.incident.search_similar`
- `sn_itsm_mcp_server.lookup_assignment_groups`
- `sn_itsm_mcp_server.lookup_users`
- `sn_itsm_mcp_server.incident.search_similar_kb`
- `sn_itsm_mcp_server.incident.get_kb_details`
- `sn_itsm_mcp_server.incident.attach_kb`

*Change management* (each takes an `operation` param):
- `sn_itsm_mcp_server.change.lifecycle` — ops `create`, `update`, `calculate_risk`, `upsert_task`, `planned_outage` (role `itil`)
- `sn_itsm_mcp_server.change.analyze` — ops `suggest_assignment_groups`, `get_risk_and_impact_data`, `suggest_cis`, `suggest_models_and_templates` (role `itil`)
- `sn_itsm_mcp_server.change.query` — ops `read`, `search`, `similar_change_and_issues`, `aggregate_by`, `get_state_info`, `check_schedules_and_conflicts`, `data_quality` (role `sn_change_read`)
- `sn_itsm_mcp_server.change.relation` — ops `list_tasks`, `list_affected_cis`, `list_approvals`, `list_incidents`, `list_problems`, `list_outages`, `list_change_policies` (role `sn_change_read`)

*Employee experience:*
- `sn_itsm_mcp_server.requester.create_incident`
- `sn_itsm_mcp_server.requester.check_status`
- `sn_itsm_mcp_server.request.modify`

*On-call (inactive by default):*
- `sn_itsm_mcp_server.oncall.on_call_lookup` — ops `who_is_on_call`, `my_next_shift`
- `sn_itsm_mcp_server.oncall.timeoff_request` — ops `analyze`, `create`

*Common:*
- `sn_itsm_mcp_server.itsm_knowledge_graph`
- `sn_itsm_mcp_server.get_session_timezone`
- `sn_itsm_mcp_server.task_approval_decision`

### 4.3 CSM MCP Server
✅ [CSM MCP Server](https://www.servicenow.com/docs/r/customer-service-management/now-assist-for-csm/csm-mcp-server.html) · [tools](https://www.servicenow.com/docs/r/customer-service-management/now-assist-for-csm/csm-mcp-server-tools-reference.html)
Tools: `get_case_tasks`, `get_customer_service_cases`, `case_summarization`, `resolution_notes_generation`, `sentiment_analysis`, `activity_response`. Role: `sn_mcp_server.viewer`; GenAI skill tools additionally restricted to `sn_customerservice_agent` and `sn_customerservice.consumer_agent`.

### 4.4 MCP for Enterprise Architecture (EA)
✅ [reference](https://www.servicenow.com/docs/r/application-portfolio-management/reference-ea-mcp-server.html) · [tool parameters](https://www.servicenow.com/docs/r/application-portfolio-management/ea-mcp-server-tool-parameters.html)
Tools (by doc section title): **Get EA Business App Insights**, **Capability Hierarchy App Resolver**, **App Rationalization Query**, **Related Entities Resolver**, **Artifact Resolver**, **Diagram change analysis**. Read-only annotations; list tools support `limit`/`offset` with `has_more`/`next_offset`.
**"Related Entities Resolver"** is directly relevant to a service-graph MCP server — its `traverse` mode does *"Multi-level impact or dependency analysis from a single CI"* with params `ci_name`, `ci_sys_id`, `direction` (`up` = impact analysis, `down`, `both`), `max_levels` (default 6, max 10), `max_nodes` (default 250, max 500), `target_class`, `include_paths` (default true), `include_svc_assoc` (default false), plus `source_table`/`target_table`/`source_names`/`rel_type_sys_id`/`path` for other modes. ✅

### 4.5 MCP Client (ServiceNow acting as MCP *client*)
✅ [Model Context Protocol Client](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-client.html) · [reference](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-reference.html)
Plugin `sn_mcp_client`. Roles `sn_mcp_client.admin`, `sn_mcp_client.viewer` (both inherited by `sn_aia.admin` / `sn_aia.viewer`). Property `sn_aia.enable_mcp_tool` (default **false**). Tables: `sn_mcp_execution_logs`, `sn_mcp_client_server_session_mapping`, `sn_mcp_server`. Server API: `MCPClientAPI`.

### 4.6 Playbooks as MCP tools
✅ [Playbooks as an MCP tool](https://www.servicenow.com/docs/r/build-workflows/workflow-studio/playbook-as-mcp-tool.html)
Playbooks can be exposed as MCP tools. Compatibility constraints: activities/lanes must start immediately; only activity types **Create Record Form, Record Form, Questionnaire, Send Email, Knowledge, Instruction, Decisions**; subflows/actions must be marked **Execution Type: MCP-compatible**; only primitive field types (no reference fields, rich text, advanced pickers, attachments, user-defined custom types).

### 4.7 Other first-party MCP servers found in release notes
✅ Store/release-note references confirm these exist: **ITSM MCP Server**, **CSM MCP Server**, **MCP Server Console** (`sn_mcp_server`), **ITOM MCP Server Console**, **Contract Management Pro MCP Server**, **MCP for Strategic Portfolio Management**, **MCP for EA**, **FSM MCP**. Store app IDs seen: ITSM MCP Server `ee43fdef936cc35057e1f0cc5cba1027`; "Model Context Protocol Server" `6e521bf447713e9482f632c4f16d434e`; Service Graph Workspace - Content `dbe4b3429723f654fe857a121153af96` (app scope `sn_sgw_content`); Workspace Builder for App Engine `0a1ba32a1b246a50a85b16db234bcb47` (scope `sn_ws_builder`).

### 4.8 "Agent Connect"
❌ **UNVERIFIED.** No ServiceNow product named "Agent Connect" appears in the official docs corpus I searched. The nearest official concepts are **AI Agent Studio** (agents), **AI Control Tower / AI Gateway** (governance + OAuth 2.1 routing), and **MCP Server Console**. A Community search only returned "Live Agent Connection" (unrelated).

---

## 5. Recommendations for the consolidated MCP server

1. **Do not rebuild what ServiceNow ships.** MCP Server Console already lets a customer expose *any* REST API (incl. Table/Aggregate/CMDB/Service Catalog) as an MCP tool, plus AI skills, subflows, actions, Knowledge Graph schemas, and playbooks — with OAuth 2.0/2.1, tool-level ACLs, monitoring, and AI Gateway governance. A third-party consolidated server must beat that on ergonomics (a unified, discoverable tool namespace; schema-aware parameters; batched traversal; cross-domain joins) — not on raw connectivity.
2. **The real gap is graph traversal.** ServiceNow's own impact analysis is an *LLM workflow* over `cmdb_rel_ci` BFS. A deterministic, depth-limited, typed graph-traversal tool (`up`/`down`/`both`, `max_levels`, `max_nodes`, `target_class`) is the highest-value thing to add — it is exactly what `Related Entities Resolver.traverse` does for EA, but generically and across the whole CMDB.
3. **Use `GET /api/now/cmdb/meta/{className}` for schema introspection** — do not hardcode CMDB class field lists; CSDM class models are extensible per instance.
4. **Name tool parameters after the documented query params** (`sysparm_query`, `sysparm_fields`, `sysparm_limit`, `sysparm_offset`, `sysparm_display_value`) so behavior matches platform conventions and operators can predict it.
5. **Budget pagination and the `Link` header.** Default `sysparm_limit` is 10000; `sysparm_limit` is applied *before* ACL evaluation, so a large limit can still return 0 rows you can see.
6. **Flag `sys_csdm_domain_model` / `sys_csdm_context` as UNVERIFIED** and probe `sys_db_object` on a live instance before exposing them. The same applies to `cmdb_rel` (wrong name — it is `cmdb_rel_ci`).
7. **Server-side code execution**: prefer a Scripted REST API you control, or the SDK's `now-sdk exec` pattern. The Table API against `sys_script` is *not* a documented execution mechanism — do not build on it.

---

## 6. Consolidated list of items I could NOT verify from an official source

| Item | Status |
|---|---|
| `sys_csdm_domain_model` table | ❌ UNVERIFIED — absent from all official docs searched |
| `sys_csdm_context` table | ❌ UNVERIFIED — absent from all official docs searched |
| `cmdb_rel` as a CMDB relationship table | ❌ UNVERIFIED / likely wrong — official name is `cmdb_rel_ci` |
| Any documented REST endpoint that executes arbitrary server-side script | ❌ Does not exist in docs; only Scripted REST API, GraphQL resolvers, `now-sdk exec`, Business Rules, Flow |
| That `POST /api/now/table/sys_script` executes a business rule | ❌ UNVERIFIED (community-only claim) |
| Exact config table name for Scripted REST Service definitions | ❌ UNVERIFIED |
| `sys_flow` / `sys_flow_definition` field-level schema | ⚠️ PARTIAL — FlowAPI/GlideFlow documented, table internals not |
| Workspace Builder / UI Builder page-configuration table names | ❌ UNVERIFIED |
| `sys_related_list` / `sys_related_list_field` as the workspace related-list backing | ⚠️ PARTIAL — `sys_ux_list_config` verified; related-list tables not |
| ServiceNow product named "Agent Connect" | ❌ Not found in official docs |
| `cmdb_rel_type` as the relationship-type table | ✅ Verified (CMDB Instance API `POST .../relation` body) |
| `svc_ci_assoc` as the service↔CI association table | ✅ Verified (Refresh Impacted Services doc) |

## 7. Files produced
All raw source docs are cached under `/home/agent/snow_research/`:
- `raw/` — ~90 markdown files pulled from `ServiceNow/ServiceNowDocs` (branch `brazil`), named by topic (e.g. `c_TableAPI.md`, `c_AggregateAPI.md`, `c_AttachmentAPI.md`, `c_ImportSetAPI.md`, `batch-api.md`, `cmdb-instance-api.md`, `cmdb-meta-api.md`, `c_ServiceCatalogAPI.md`, `scripted-graph-ql.md`, `itsm_mcp_tools.md`, `mcp_csm-tools.md`, `mcp_ea-tools.md`, `sgw-*.md`).
- `snowdocs/` — shallow git clone of `ServiceNow/ServiceNowDocs` (branch `brazil`), sparse-checked-out to `servicenow-platform`, `api-reference`, `application-development`, `it-service-management` (8,773 files) — used for the exhaustive `sys_csdm_*` / `cmdb_class_info` / `cmdb_rel_ci` greps.
- `sgw_*.json` / `sgw_*.txt` — Service Graph Workspace landing + all six views, fetched via the official FluidTopics content API (`www.servicenow.com/docs/api/khub/maps/{mapId}/topics/{topicId}/content`), since the SGW landing pages are **not** present in the public `ServiceNowDocs` GitHub mirror.
