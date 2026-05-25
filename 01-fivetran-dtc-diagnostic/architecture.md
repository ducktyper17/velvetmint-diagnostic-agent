# Architecture

## High-level system diagram

```
                 ┌──────────────────────────────────────────────────────┐
                 │            Founder's browser (Maya, VelvetMint)      │
                 │                                                      │
                 │   Next.js 15 + shadcn/ui dashboard on Cloud Run      │
                 │   - /                  marketing + sign in           │
                 │   - /dashboard         live diagnosis chat           │
                 │   - /diagnoses/[id]    historical diagnosis report   │
                 └──────────────┬─────────────────────────▲─────────────┘
                                │ POST /diagnose          │ SSE stream
                                │ (HTTPS, JWT)            │ (text/event-stream)
                                ▼                         │
                 ┌──────────────────────────────────────────────────────┐
                 │     Agent service (FastAPI, Cloud Run, Python 3.11)  │
                 │                                                      │
                 │   POST /diagnose                                     │
                 │     - Persists conversation in MongoDB               │
                 │     - Spawns agent_loop, streams events back via SSE │
                 │                                                      │
                 │   GET  /diagnoses/{id}    final report               │
                 │   GET  /healthz           liveness                   │
                 └──────────────┬─────────────────────────┬─────────────┘
                                │                         │
              ┌─────────────────┘                         └─────────────────┐
              │                                                             │
              ▼                                                             ▼
  ┌────────────────────────┐                                  ┌─────────────────────────┐
  │   Vertex AI / Gemini 3 │                                  │  Fivetran MCP server    │
  │   (Agent Builder       │                                  │  (HTTP transport)       │
  │    orchestration)      │                                  │                         │
  │                        │   tool calls (JSON over HTTP)    │  161 tools, we use:     │
  │  - System prompt       │  ─────────────────────────────▶  │   list_connections      │
  │  - Few-shot examples   │  ◀─────────────────────────────  │   create_connection     │
  │  - Tool schema         │   tool results                   │   run_connection_setup… │
  │  - Reasoning trace     │                                  │   sync_connection       │
  │                        │                                  │   get_connection_state  │
  │                        │                                  │   modify_connection_…   │
  └────────────────────────┘                                  │   resync_connection     │
                                                              │   get_connection_schema │
                                                              └────────────┬────────────┘
                                                                           │ Fivetran REST API
                                                                           ▼
                                                              ┌─────────────────────────┐
                                                              │   Fivetran (managed)    │
                                                              │                         │
                                                              │  Source connectors:     │
                                                              │   Shopify               │
                                                              │   Klaviyo               │
                                                              │   Meta Ads              │
                                                              │   Google Ads            │
                                                              │   TikTok Ads            │
                                                              │   Stripe                │
                                                              │   Yotpo (reviews)       │
                                                              │                         │
                                                              │  Destination:           │
                                                              │   BigQuery              │
                                                              └────────────┬────────────┘
                                                                           │ rows materialized
                                                                           ▼
                                                              ┌─────────────────────────┐
                                                              │      BigQuery           │
                                                              │                         │
                                                              │  fivetran_velvetmint    │
                                                              │   .shopify_orders       │
                                                              │   .klaviyo_events       │
                                                              │   .meta_ads_insights    │
                                                              │   .google_ads_metrics   │
                                                              │   .tiktok_ads_metrics   │
                                                              │   .stripe_charges       │
                                                              │   .yotpo_reviews        │
                                                              └────────────┬────────────┘
                                                                           │ analytical queries
                                                                           ▼
                                                              ┌─────────────────────────┐
                                                              │  diagnostic_engine.py   │
                                                              │                         │
                                                              │  ROAS by channel        │
                                                              │  List decay rate        │
                                                              │  Funnel conv. by browser│
                                                              │  Refund / dispute rate  │
                                                              │  Creative fatigue       │
                                                              │  ... (8–12 checks)      │
                                                              └────────────┬────────────┘
                                                                           │ findings
                                                                           ▼
                                                                ┌──────────────────────┐
                                                                │   MongoDB Atlas      │
                                                                │                      │
                                                                │  conversations       │
                                                                │  diagnoses           │
                                                                │  agent_traces        │
                                                                │  fivetran_state      │
                                                                └──────────────────────┘

  ┌──────────────────────────┐
  │  Cloud Function          │
  │  /start-diagnosis        │ ─── HTTPS webhook target for the front-end
  │  (thin trigger that      │     and any external "schedule a diagnosis"
  │   forwards to the agent) │     integrations.
  └──────────────────────────┘
```

## Component responsibilities

### Frontend (Next.js 15, shadcn/ui, Tailwind)
- Renders the founder's chat interface, the live agent reasoning panel, and the
  final structured diagnosis card.
- Subscribes to `/diagnose` via the browser's `EventSource` for SSE events.
- Reads historical diagnoses from `/diagnoses/{id}`.
- Hosted on Cloud Run as a separate service (so the agent service can scale
  independently).

### Agent service (FastAPI, Python 3.11)
- Single entrypoint endpoint `POST /diagnose`.
- Persists each turn (user question, agent reasoning, tool calls, tool results,
  final report) in MongoDB so a refresh resumes the stream.
- Holds the agent loop in a `BackgroundTask` and streams events to the client via
  `StreamingResponse(media_type="text/event-stream")`.
- Stateless across instances; horizontal scale on Cloud Run is fine because state
  lives in MongoDB.

### Agent loop (`agent_loop.py`)
- Classic ReAct: model → tool call → tool result → model → ... → final answer.
- Talks to Gemini 3 via Vertex AI's `google-cloud-aiplatform` SDK.
- Tool dispatch table: `setup_connector`, `trigger_sync`, `check_sync_status`,
  `query_synced_data`, `run_diagnostic_battery`, `finalize_diagnosis`.
- Each iteration emits an SSE event so the UI can show the reasoning live.
- Hard cap of 25 iterations per diagnosis to avoid infinite loops.

### Fivetran MCP integration (`tools.py`)
- HTTP client that speaks to the Fivetran MCP server (run alongside the agent or
  hosted separately — TBD; for the demo, easiest is to run it as a sidecar
  container in the same Cloud Run service or as a separate Cloud Run service).
- Wraps the MCP tool surface in typed Python functions so the agent loop has a
  clean interface.
- Honors `FIVETRAN_ALLOW_WRITES=true` for `create_connection`,
  `modify_connection`, `resync_connection`, `sync_connection`,
  `modify_connection_schema_config`. Read-only tools (`list_connections`,
  `get_connection_details`, `get_connection_state`, `get_connection_schema_config`,
  `run_connection_setup_tests`) work without it.

### Diagnostic engine (`diagnostic_engine.py`)
- BigQuery client that runs a fixed battery of analytical queries against the
  Fivetran-synced tables.
- Each query returns a `Finding(metric, current_value, baseline_value,
  delta_pct, dollar_impact, recommended_fix)`.
- Findings are scored, ranked, and the top 3 are returned to the agent for
  inclusion in the final report.

### Persistence (MongoDB Atlas)
- `conversations` — `{_id, user_id, brand, messages: [...], created_at}`
- `diagnoses` — `{_id, conversation_id, question, findings: [...], status, ...}`
- `agent_traces` — `{_id, diagnosis_id, iteration, role, content, tool_call,
  tool_result, latency_ms}` — used for debugging + the demo replay.
- `fivetran_state` — `{_id, brand, connectors: [{source, connection_id, status,
  last_sync_at}]}` cached for fast UI rendering, refreshed from MCP on each
  diagnosis.

### Cloud Function (`/start-diagnosis`)
- Optional thin HTTP trigger.
- Lets the frontend POST to a stable Cloud Function URL that fans out to the
  current Cloud Run revision of the agent service.
- Used for: scheduled "weekly health check" diagnoses, demo button on the
  marketing page.

## Data flow — happy path

1. Founder types a question in the dashboard, hits send.
2. Browser opens an `EventSource` to `/diagnose?conversation_id=...`.
3. Agent service writes the user message to MongoDB, kicks off the agent loop.
4. Agent loop calls Gemini 3 with the system prompt + few-shot examples + the
   conversation so far. Gemini returns a tool call: `setup_connector(source="shopify")`.
5. `tools.setup_connector` POSTs to the Fivetran MCP server, which calls
   Fivetran's REST API, which creates a Shopify connection.
6. The agent loop emits an SSE event: `event: tool_result\ndata: {...}\n\n`.
7. Steps 4–6 repeat for each source. Then `trigger_sync` for each.
8. After syncs complete (polled via `check_sync_status`), the agent calls
   `query_synced_data` which delegates to `diagnostic_engine.run_battery()`.
9. Diagnostic engine returns ranked `Finding` objects.
10. Agent calls `finalize_diagnosis` with the top 3 findings, which writes the
    final report to MongoDB and emits a terminal SSE event: `event: done\ndata: {...}\n\n`.
11. Browser closes the `EventSource`. Dashboard renders the final structured card
    (problem / root cause / dollar impact / fix) for each finding.

## Demo-mode shortcuts

For the 3-minute video, we cannot wait for real syncs (a Shopify+Klaviyo+Meta sync
of 90 days of data takes 5–30 min). So the demo uses two shortcuts that are
**clearly disclosed in the README** but kept invisible in the demo:

1. **Pre-warmed Fivetran connections.** The 7 connectors already exist and have
   already synced 90 days of data into BigQuery. The agent's `setup_connector`
   call in demo mode actually calls `get_connection_details` on an existing
   connection (idempotent) so the visible behavior — "agent set up the connector"
   — is real, just fast.
2. **A scripted anomaly seed.** The synced data has been seeded with a known set
   of anomalies (TikTok creative fatigue starting May 2, popup broken May 3,
   iOS Safari checkout JS error May 8) so the diagnostic engine reliably finds
   them and we can rehearse.

These shortcuts are documented in `SCAFFOLD-NOTES.md` and disclosed in the
Devpost writeup. The agent's *reasoning, tool-calling, and final report
generation are fully real* — only the timing is compressed.

## Security / hackathon-judges-checklist

- All secrets in **Google Secret Manager**, surfaced to Cloud Run as env vars.
- Fivetran API key has **trial-account-only** scope — no production data.
- MongoDB Atlas has **IP allowlist + connection-string auth**.
- Service-to-service auth is **Cloud Run IAM** (`roles/run.invoker`).
- BigQuery access is **dataset-scoped** to `fivetran_velvetmint` only.
- Frontend talks to the agent through a **signed identity token** via Cloud Run's
  built-in OIDC; no API keys are shipped to the browser.
- Repo is public on GitHub with **Apache-2.0**; no `.env`, no keys, no PII in the
  commit history.
