# Partner MCP Server Cheatsheet

Quick reference for what each of the 6 partner MCP servers exposes. Use this to decide if a feature is feasible on a given track. Sources: each partner's resource page on Devpost (linked per section).

---

## Arize Phoenix MCP — [partner page](https://rapid-agent.devpost.com/details/arize-resources)

**Package**: `@arizeai/phoenix-mcp` — npm, runs via `npx`
**Auth**: `PHOENIX_API_KEY`, `PHOENIX_HOST` (Phoenix Cloud free tier or self-hosted)
**Hard constraint (per partner page)**: the Arize track **requires a code-owned agent runtime**. Gemini CLI, Agent Platform SDK, Google ADK, Agent Runtime, or Cloud Run all qualify. **The low-code Agent Builder UI alone is not supported** because you can't instrument visual workflows for tracing. Doesn't affect us (we're on Fivetran) but rules out a UI-only approach if we pivot.
**Required instrumentation**: OpenInference via one of:
- `openinference-instrumentation-google-adk` — for ADK agents
- `openinference-instrumentation-vertexai` — for Gemini SDK / generative_models
- `openinference-instrumentation-google-genai` — for the unified google-genai SDK
**Reference repo**: https://github.com/Arize-ai/gemini-hackathon (end-to-end traced Gemini agent + Phoenix MCP + evaluations)
**Hackathon contact**: Richard Young — ryoung@arize.com

### Tools exposed

| Tool | What it does |
|---|---|
| `list-prompts`, `get-prompt`, `get-latest-prompt`, `upsert-prompt` | Version-controlled prompt management |
| `list-prompt-versions`, `get-prompt-version`, `add-prompt-version-tag` | Prompt versioning |
| `list-projects`, `get-project` | Project (workspace) management |
| `list-traces`, `get-trace` | Read trace data (LLM/agent runs) |
| `get-spans`, `get-span-annotations` | Span-level data |
| `list-sessions`, `get-session` | Conversation-level groupings |
| `list-annotation-configs` | Annotation schemas |
| `list-datasets`, `get-dataset`, `get-dataset-examples`, `add-dataset-examples` | Curated example sets |
| `list-experiments-for-dataset`, `get-experiment-by-id` | LLM-as-judge experiments |

### Best fit for
Agents that **evaluate other agents/AI**, monitor production AI quality, run LLM-as-judge experiments. Phoenix is a tool *for* AI builders.

---

## Elastic MCP — [partner page](https://rapid-agent.devpost.com/details/elastic-resources)

**Trial**: free Elastic Cloud **Serverless** project at https://cloud.elastic.co (also available via Google Cloud Marketplace). 14 days. Forum reports the trial expires before judging (June 22+) — same trial-expiry risk we have with Fivetran.
**Two servers exist**:
1. (Deprecated) `elastic/mcp-server-elasticsearch` — Docker container, tools: `list_indices`, `get_mappings`, `search`, `esql`, `get_shards`
2. (Current, 9.2+) **Elastic Agent Builder MCP server** — built into Kibana with NO extra config required. Tools live in the Agent Builder Tools UI. The endpoint URL is visible in the Tools UI.

**Auth**: API key with `agentBuilder:read` privilege (current) / direct ES API key (deprecated)

### Capabilities highlighted by Elastic for this hackathon
- **Hybrid retrieval** (semantic + keyword + vector) over structured or unstructured data via MCP
- **ELSER** semantic model runs automatically for hybrid search
- **Custom tools backed by ES|QL** — define a tool that wraps an ES|QL query, exposed over MCP
- **Workflow tools that reach across systems** — multi-step workflows that call external APIs, can invoke subagents with their own skills
- **Built-in connectors** for Google Drive, Confluence, SharePoint, GitHub, databases
- **Memory layer** — write enriched facts/summaries back into Elasticsearch as a context layer

### Tools exposed (current — Agent Builder)
- Exposes any tools you build in Elastic Agent Builder (custom tools per project)
- Plus built-in ES|QL execution
- Plus index search

### Tools exposed (deprecated server, but still widely referenced)
- `search` — Query DSL search
- `esql` — Execute ES|QL queries (the new SQL-like syntax)
- `list_indices`, `get_mappings`, `get_shards`
- Some community forks add: `semantic_search` (kNN vector search), `aggregate`, `get_document`

### Best fit for
Search-heavy agents — hybrid keyword + vector retrieval, log analysis at scale, semantic search over unstructured corpora.

---

## Fivetran MCP — [partner page](https://rapid-agent.devpost.com/details/fivetran-resources) — OUR TRACK

**Trial**: 14 days at https://fivetran.com/signup. Same trial-expiry risk for judging — see `00-shared/trial-expiry-risk.md`.
**Same API key works for both MCP and REST API.** Auth setup: https://fivetran.com/docs/rest-api/getting-started#authentication

### Two officially supported integration paths (we use BOTH)
1. **MCP** — open-source example server at https://github.com/fivetran/fivetran-mcp. Fivetran explicitly recommends forking and extending it. **This is a hackathon advantage** — most teams will use the server as-is; we extend it.
2. **REST API** — direct: https://fivetran.com/docs/rest-api. Example project: https://github.com/fivetran/api_framework. The rules (Section 7.A) still require the MCP server, but we can use REST for anything MCP doesn't cover.

The rules require MCP integration. The partner page documents both as first-class. Plan: MCP is the agent's primary tool surface; REST API is used only where the example MCP doesn't expose a needed endpoint (we'll add those as tools in our fork).

**Destination quickstart**: BigQuery — https://fivetran.com/docs/destinations/bigquery/setup-guide
**Write mode**: `FIVETRAN_ALLOW_WRITES=true` (REQUIRED for the agent to autonomously create connectors)

### Key tools (~25 enabled by default of 161 total)

| Tool | What it does |
|---|---|
| `list_connections` | List all Fivetran connections |
| `create_connection` | Create a NEW connection (write mode) |
| `get_connection_details` | Status, last sync time, config |
| `modify_connection` | Update existing connection |
| `delete_connection` | Remove connection |
| `get_connection_state` | Detailed sync state |
| `sync_connection` | Trigger a data sync |
| `resync_connection` | Trigger historical re-sync |
| `resync_tables` | Re-sync specific tables |
| `run_connection_setup_tests` | Diagnostic tests |
| `create_connect_card` | Create a connect-card token |
| `get_connection_schema_config` | Schema/table sync config |
| `modify_connection_schema_config` | Update schema config |
| `reload_connection_schema_config` | Reload from source |

Plus `search` + `execute` meta-tools that unlock the entire 161-endpoint REST API on demand.

### Best fit for
Agents that **autonomously orchestrate data pipelines** across SaaS sources. Use the write-mode connector-creation tools — that's the killer use of Fivetran.

---

## GitLab MCP — [partner page](https://rapid-agent.devpost.com/details/gitlab-resources)

**Trial**: **30-day GitLab Ultimate trial** at https://about.gitlab.com/free-trial/. **This is the only partner whose trial covers the full judging window** (June 22 – July 6) — if we were to pivot to GitLab, no trial-expiry risk. Each trial includes Duo Agent Platform with 24 credits per user.
**Status notes from partner**: Custom agents GA, Custom flows Beta, AI Catalog GA, MCP server Beta. MCP doc: https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/
**Setup gotcha**: external tools calling GitLab via MCP must set a default Duo namespace. In-GitLab usage works without it.

**Two servers**: official (built into GitLab 18.3+, requires GitLab Duo) + community (`zereight/gitlab-mcp`, `jmrplens/gitlab-mcp-server` with up to 1006 endpoints)
**Auth**: OAuth 2.0 Dynamic Client Registration (official) or PAT
**Transport**: HTTP (recommended) or stdio via `mcp-remote`

### Tools (official, ~15 in v18.11)

| Category | Tools |
|---|---|
| Issues | `get_issue`, `list_issues`, `create_issue`, `update_issue`, `add_issue_comment` |
| MRs | `get_merge_request`, `list_merge_requests`, `get_mr_commits`, `get_mr_changes`, `add_mr_comment` |
| Pipelines | `list_pipelines`, `get_pipeline`, `list_pipeline_jobs`, `get_pipeline_job_log` |
| Projects | `get_project`, `list_projects`, `search_projects` |
| Server | `get_server_info` |

### Tools (community `jmrplens` server — much broader)
- Repositories, branches, files (read/write)
- Wiki (read/write)
- Releases, tags, milestones
- Labels, work items
- `gitlab_analyze` meta-tool with 11 LLM-assisted analyses (code review, pipeline failure diagnosis, security review, release notes, etc.)

### Best fit for
Agents that take **real actions in a software org** — open MRs, create epics, triage issues, drive pipelines. Useful for code AND for non-code (wikis, project management).

---

## MongoDB MCP — [partner page](https://rapid-agent.devpost.com/details/mongodb-resources)

**Trial**: Atlas M0 free tier — always free, no expiry. Safest partner for the trial-expiry problem.
**Pre-loaded demo data**: `sample_mflix.embedded_movies` already contains vector embeddings (instant Vector Search demo). Or bring your own dataset.
**Embedding model constraint per partner page**: "Embedding model should be one of MongoDB provided or Google provided." So Voyage AI (MongoDB-owned since 2024) and Google's text-embedding models are both fine. OpenAI embeddings would violate both the partner page and the hackathon AI rule.

**Package**: `mongodb-js/mongodb-mcp-server` (official)
**Auth**: connection string + optional Atlas API keys
**Run**: stdio or HTTP, also containerized via Docker

### Tools

| Category | Tools |
|---|---|
| Atlas mgmt | `atlas-list-orgs`, `atlas-list-projects`, `atlas-create-project`, `atlas-list-clusters`, `atlas-create-free-cluster`, `atlas-inspect-cluster`, `atlas-list-db-users`, `atlas-create-db-user` |
| Database ops | `find`, `aggregate`, `insert-many`, `update-many`, `delete-many`, `count`, `create-index` |
| Metadata | `list-databases`, `list-collections`, `collection-schema`, `collection-indexes`, `db-stats` |
| Vector search | Create/manage vector indexes, semantic search via `$vectorSearch` in `aggregate` |
| Knowledge | `search-knowledge`, `list-knowledge-sources` (MongoDB docs) |

### Auto-embedding
If `VOYAGE_API_KEY` is set, the MCP auto-embeds text fields on `insert-many` and auto-generates `queryVector` on `$vectorSearch` queries. **Big deal** — removes embedding boilerplate.

### Best fit for
Hybrid retrieval (semantic + structured filters), agent state storage, knowledge bases with vector search.

---

## Dynatrace MCP — [partner page](https://rapid-agent.devpost.com/details/dynatrace-resources)

**Trial**: 15-day free trial. Forum-confirmed concern: trial may expire before judging starts (June 22). If we ever pivot here, same demo-replay approach as Fivetran.
**Partner-specific angle**: Dynatrace is positioning itself as observability for *AI agents themselves* (OpenTelemetry traces from Vertex AI, Gemini, coding agents). Token spend, tool calls, latency, errors. The "AI Coding Agent Monitoring" feature lists support for Claude Code / Gemini CLI / Codex CLI / OpenCode / GitHub Copilot SDK — note: we can only ship something that *uses* Gemini-based agents per the hackathon AI rules, so any demo here would need to be Gemini-only.
**Telemetry pipeline tool**: Bindplane (Google Edition) — free OpenTelemetry-native pipeline. Useful if we ever needed multi-destination telemetry.

**Package**: `@dynatrace-oss/dynatrace-mcp-server` (npm)
**Auth**: Platform bearer tokens with `mcp-gateway:servers:invoke`, `mcp-gateway:servers:read` permissions + data scopes (`storage:logs:read`, etc.)

### Tools

| Category | Tools |
|---|---|
| Observability | `list_problems`, `list_vulnerabilities`, `list_exceptions`, `get_kubernetes_events` |
| Query | `execute_dql`, `verify_dql`, `generate_dql_from_natural_language`, `explain_dql_in_natural_language` |
| Entity discovery | `find_entity_by_name` |
| Davis intelligence | `chat_with_davis_copilot`, `list_davis_analyzers`, `execute_davis_analyzer` |
| Forecasting | `Forecasting Agent` (statistical timeseries forecasting), `Changepoint Agent` (find outliers/trend changes) |
| Automation | `create_workflow_for_notification`, `send_slack_message`, `send_email`, `send_event` |
| Sharing | `create_dynatrace_notebook` |

### Best fit for
**Timeseries forecasting** + changepoint detection + observability across non-IT domains (this is the underused angle). DQL is powerful — natural-language to DQL conversion is built in.

---

## Choosing across MCPs

| If your agent's core job is... | Use this MCP |
|---|---|
| Evaluating other AI outputs / running LLM-as-judge | **Arize Phoenix** |
| Semantic/hybrid search across messy text | **Elastic** or **MongoDB** |
| Wiring up SaaS data pipelines across many sources | **Fivetran** |
| Taking actions in a code/ops platform | **GitLab** |
| Storing + retrieving with hybrid semantic + structured | **MongoDB** |
| Querying live observability data + forecasting | **Dynatrace** |

The single biggest mistake is picking a track where the MCP is decorative. Pick the track where the MCP does the work no other tool can.
