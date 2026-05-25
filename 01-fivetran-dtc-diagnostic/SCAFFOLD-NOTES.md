# Scaffold notes

Snapshot of what is in this scaffold, what remains to wire up, and the
risks worth watching. Use this as the launch checklist for Day 1.

## What is complete

### Documentation
- `README.md` — project intro, problem, user, value prop, stack, demo flow.
- `architecture.md` — full system diagram (text), component responsibilities,
  data flow, demo-mode shortcuts, security checklist.
- `demo-script.md` — beat-by-beat 3-minute video script in 15-second chunks.
- `build-plan.md` — day-by-day from May 24 to June 11, with blocking
  dependencies on partner approvals flagged.
- `agent/README.md` — local development instructions and stub map.
- `frontend/README.md` — Next.js 15 component / route / dependency plan.
- `infra/README.md` — gcloud commands for all four services (agent,
  Fivetran MCP, frontend, Cloud Function).
- `SCAFFOLD-NOTES.md` — this file.

### Agent service (Python)
- `agent/pyproject.toml` — Python 3.11 project with real, conservative
  PyPI versions for FastAPI, uvicorn, sse-starlette, pydantic v2,
  google-cloud-aiplatform, mcp, pymongo, google-cloud-bigquery, httpx,
  structlog, tenacity. Versions I was not certain about are flagged with
  `# TODO: confirm latest version` comments instead of being made up.
- `agent/.env.example` — every env var the agent reads, documented.
- `agent/src/agent/__init__.py` — package init.
- `agent/src/agent/config.py` — Pydantic-Settings runtime config with
  SecretStr wrapping for all secrets.
- `agent/src/agent/main.py` — FastAPI app: `/healthz`, `/diagnose` (SSE),
  `/diagnoses/{id}`. Lifespan for shared HTTP client. uvicorn entrypoint.
- `agent/src/agent/agent_loop.py` — ReAct loop with `AgentEvent`-based
  streaming, tool dispatch, iteration cap, deterministic stub for the
  Gemini call so the loop is testable today.
- `agent/src/agent/tools.py` — `FivetranMCPClient` (httpx async client with
  tenacity retries) plus typed wrappers `setup_connector`, `trigger_sync`,
  `check_sync_status`, `query_synced_data`. JSON-RPC 2.0 envelope.
- `agent/src/agent/prompts.py` — system prompt that constrains the agent
  to a fixed tool surface plus 3 few-shot examples covering revenue down,
  AOV-vs-profit, repeat-purchase decline.
- `agent/src/agent/diagnostic_engine.py` — `Finding` dataclass, 12 named
  metrics, parallel `run_battery`, demo-aligned stub data, three working
  rule-engine interpretations matching the demo script.

### Infra
- `infra/cloudbuild.yaml` — working Cloud Build config: build → push to
  Artifact Registry → deploy to Cloud Run with secrets and env vars wired.
  Just needs a Dockerfile (Day 2 task).

## What is stubbed

Everything below is clearly marked with `TODO` in the code. They are
ordered by the day each lands per the build plan.

| # | Stub | File | Day | Hours |
|---|---|---|---|---|
| 1 | Real Vertex AI / Gemini 3 call | `agent_loop.py::_call_gemini` | 2 | 4 |
| 2 | Dockerfile for the agent | `agent/Dockerfile` (missing) | 2 | 1 |
| 3 | Confirm MCP HTTP endpoint path + SSE behavior | `tools.py::FivetranMCPClient.call_tool` | 3 | 2 |
| 4 | Parse real `list_connections` / `create_connection` responses | `tools.py::_iter_connections`, `_extract_connection_id` | 3 | 2 |
| 5 | Per-source connector `config` payloads (OAuth, schemas) | `tools.py::setup_connector` | 3-4 | 4 |
| 6 | MongoDB lifespan + persistence | `main.py` (lifespan, `/diagnose`, `/diagnoses/{id}`) | 5 | 4 |
| 7 | Seed VelvetMint into BigQuery | `scripts/seed_velvetmint.py` (missing) | 6 | 6 |
| 8 | Real BigQuery queries for 12 metrics | `diagnostic_engine.py::run_named_query` + SQL bodies | 7 | 8 |
| 9 | Per-metric anomaly interpretation rules (the other 9) | `diagnostic_engine.py::_interpret_rows` | 7-10 | 4 |
| 10 | Next.js frontend (whole project) | `frontend/` | 8-9 | 16 |
| 11 | Cloud Function `dtc-start-diagnosis` | `infra/functions/start_diagnosis/main.py` (missing) | 11 | 2 |
| 12 | Multi-brand registry lookup | `agent_loop.py::_resolve_destination_id`, `_resolve_group_id` | 12 | 2 |
| 13 | Connector status polling helper + UI animation | new helper + frontend | 13 | 4 |
| 14 | Demo-mode flag wiring (pre-warmed connections path) | `tools.py`, `main.py` | 13 | 2 |
| 15 | Apache-2.0 LICENSE at workspace root | `../LICENSE` (missing) | 16 | 0.25 |
| 16 | Tests (pytest unit + 1 e2e replay test) | `agent/tests/` (missing) | rolling | 6 |
| 17 | Devpost writeup, demo video, captions | external | 14-16 | 12 |

## Data and keys we still need

- **Fivetran API key + secret** — required for the MCP server to make
  real calls. Apply on Day 1 (signup is fast; trial is 14 days so don't
  start until Day 8).
- **Service-account JSON** for `dtc-agent-sa` — generated after the SA
  exists in GCP.
- **MongoDB Atlas SRV connection string** — copy from the Atlas UI.
- **GCP project id + project number** — needed for `cloudbuild.yaml`
  substitutions.
- **Sandbox accounts for each source** — Shopify Partner dev store,
  Klaviyo trial, Meta Business sandbox app, Google Ads test account,
  TikTok for Business, Stripe test mode, Yotpo trial. SETUP.md at the
  workspace root has the signup links.
- **Domain (optional)** — Cloud Run's `*.run.app` URLs are fine for the
  demo; only needed if you want a polished public URL.

## Estimated remaining work to a working demo

Adding the items above:

| Phase | Hours |
|---|---|
| Phase 1 (prove the loop, Days 1-7) | 22 |
| Phase 2 (real integrations + dashboard, Days 8-13) | 32 |
| Phase 3 (polish + submit, Days 14-19) | 18 |
| Buffer (failures + retries) | 8 |
| **Total** | **~80 person-hours** |

That fits in the 19-day window for one focused builder spending ~4
hours/day, or two builders spending ~2 hours/day each. The build plan
spreads it deliberately so no single day is more than ~6 hours.

## Top 3 risks

### 1. Gemini 3 + Agent Builder access (high impact, medium probability)
Vertex AI Gemini 3 may be limited to specific allowlisted projects, and
"Agent Builder" branding in 2026 may have been consolidated under a
different product name. **Mitigation:**
- Day 1, request access via the GCP console and the hackathon Discord.
- If Gemini 3 is gated, fall back to Gemini 2.5 — the prompt structure
  is identical, and judges care about the *use* of the model more than
  the version.
- If Agent Builder UI is unavailable, run the agent loop directly via the
  `vertexai` Python SDK with function calling. The hackathon brief allows
  this; it just costs us the Agent Builder visual story.

### 2. Fivetran trial constraints break the connector-creation demo (high impact, medium probability)
The demo's killer move is the agent autonomously calling
`create_connection` for 7 sources. If the Fivetran trial throttles
connector creation, restricts certain sources, or only allows manual
authorization, the live segment of the video falls apart.
**Mitigation:**
- Day 3, validate on a single test source (Shopify) end-to-end before
  committing.
- If write mode is restricted to ≤4 sources, scope the demo to those 4
  sources. The story still works — fewer sources, same narrative.
- If write mode is gated entirely, pre-record beats 3-5 of the demo (the
  connector setup) and run beats 6-10 live. Disclose in Devpost. Judges
  value reasoning quality over realism.

### 3. SSE through Cloud Run is flaky, breaking the live reasoning UX (medium impact, medium probability)
Cloud Run has a 60-minute request timeout but historical issues with
streaming responses, gzip buffering, and idle connection handling.
**Mitigation:**
- `sse-starlette` already disables gzip + nginx-style buffering via the
  `X-Accel-Buffering: no` header.
- 15-second `ping` keeps the connection alive through any intermediate
  proxies.
- Day 5 spike: run a 3-minute synthetic SSE stream end-to-end through
  Cloud Run and confirm no events drop.
- Last-ditch fallback: switch from SSE to short-poll (`GET /diagnoses/{id}/events?since=ts`)
  with a 500 ms interval. The UI looks identical to the user; only the
  network shape changes.

## Things to be aware of (not risks, just heads-ups)

- **The MCP server may not be HTTP-first by default.** The official
  Anthropic MCP SDK supports both stdio and HTTP transports. The Fivetran
  server was originally stdio-only; confirm HTTP is supported on Day 3
  before building around it. If not, run an HTTP wrapper in front of
  stdio (~30 lines of Python).
- **Gemini function-calling JSON shape varies between versions.** The
  `_call_gemini` stub abstracts this. When wiring the real call, write
  the response-parser carefully — it's the most common breakage point.
- **BigQuery query latency is bursty in `us-central1` during workday
  hours.** Cache the 12-query results per (brand, day) in MongoDB so
  successive demo runs feel instant.
- **Demo-mode disclosure matters for judging integrity.** Be explicit in
  the Devpost writeup about which segments are pre-recorded. Judges
  reward honesty — and the *agent's reasoning* is fully real either way.

## Suggested next actions

1. Read this file end-to-end.
2. Apply for the GCP $100 credit and start the GCP free trial (SETUP.md).
3. Sign up for Fivetran (do not start the trial clock; just create the
   account).
4. Create the GCP project, run the one-time prereqs in `infra/README.md`.
5. Day-2 work: write the Dockerfile, do the first real Gemini call.
