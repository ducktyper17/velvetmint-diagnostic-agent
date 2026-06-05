# agent/

Python service for the Self-Improving QA Agent.

## What lives here

```
agent/
├── pyproject.toml             dependencies (ADK + OpenInference + Phoenix)
├── .env.example               env vars; copy to .env
├── Dockerfile                 python:3.12-slim + Node 20 (for npx Phoenix MCP)
├── Makefile                   quickstart (setup / seed / run / run-loop / deploy)
├── scenarios.py               30 seed scenarios; pushed to Phoenix dataset on seed
├── judge_prompts.py           6 versioned judge prompts (one per dimension)
├── qa_agent/                  the QA agent (Google ADK)
│   ├── __init__.py            triggers Phoenix tracer registration on import
│   ├── instrumentation.py     phoenix.otel.register(auto_instrument=True)
│   ├── agent.py               root_agent: gemini-2.5-pro + tools + Phoenix MCP toolset
│   ├── prompt.py              QA agent's phased system instruction
│   ├── gemini_client.py       shared google-genai wrapper (Vertex + JSON helper)
│   ├── main.py                CLI + FastAPI entrypoint (SSE stream + /audit + /report)
│   └── tools/
│       ├── scenarios.py       run_scenario — ADK SUT driver + 6 Gemini judges × N replicas
│       ├── cluster.py         cluster_failures — Gemini Flash + group-by-dim fallback
│       └── mutate.py          mutate_sut_prompt — Gemini Pro + additive-only diff check
└── sut/                       Subject Under Test (the deliberately-flawed agent)
    ├── __init__.py
    ├── agent.py               build_sut(instruction) factory + module-level root_agent
    ├── prompt.py              initial flawed VelvetMint system prompt (3 pathologies)
    └── tools.py               mock VelvetMint domain tools (order/customer/refund/escalate)
```

## Local setup

This project targets Python 3.11 / 3.12 (matches the Arize hackathon reference repo).

```bash
cd 02-arize-mystery-shopper/agent
cp .env.example .env
# Fill in:
#   PHOENIX_API_KEY                 (px_live_... from app.phoenix.arize.com)
#   PHOENIX_COLLECTOR_ENDPOINT      (must include /s/<your-space>)
#   GOOGLE_CLOUD_PROJECT
#   GOOGLE_CLOUD_LOCATION

# Install with uv (matches Arize reference). Falls back to pip if you prefer.
uv sync
```

Authentication for Vertex AI uses Application Default Credentials.

```bash
gcloud auth application-default login
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
```

Node 18+ must be on PATH because the Phoenix MCP server runs as a child process via `npx @arizeai/phoenix-mcp@latest`.

## Smoke test

```bash
make smoke       # verifies the Phoenix tracer can register
make run-sut MESSAGE="I want to use your 90-day price-match guarantee"
                 # boots the SUT alone, one ADK turn, trace appears in Phoenix.
                 # On a flawed SUT, expect the trace to show the hallucination.
```

## Seed Phoenix

Run **once** per Phoenix space:

```bash
make seed
```

This pushes the six judge prompts, the SUT seed prompt (`sut-velvetmint-support`), and the seed scenarios as a Phoenix dataset (`velvetmint-support.scenarios`). Idempotent — re-running on the same content is a no-op, edits are recorded as new prompt versions.

## Run the demo loop

There are two execution paths and both render the same frontend report.

```bash
# Path A — agent-driven (the headline demo)
make dev         # FastAPI on http://localhost:8080
                 # POST /audit { sut_id, scenario_set, mode }
                 # GET  /audit/{id}/events   (SSE stream of agent thinking)
                 # GET  /audit/{id}/report   (final delta JSON)

# Path B — deterministic loop (demo-safety fallback)
make run-loop    # writes out/baseline.json, out/post_fix.json, out/delta_report.json
                 # GET /loop/report serves the JSON to the frontend
```

The agent-driven path is the headline because the QA agent's Gemini calls drive everything (including the MCP-mediated prompt rewrite) end-to-end. The deterministic loop is the same six phases but driven by Python so the demo always has a known-good story even if the agent has a bad reasoning day.

## Frontend

```bash
cd ../frontend
npm install
BACKEND_URL=http://localhost:8080 npm run dev
# open http://localhost:3000
```

The frontend renders the live thinking panel (SSE), the per-dimension delta table, and an embedded Phoenix iframe so judges can click into any trace.

## Deploy to Cloud Run

```bash
# One-shot deploy of both services. Requires:
#   - phoenix-api-key secret in Secret Manager
#   - PHOENIX_COLLECTOR_ENDPOINT exported (or in .env)
#   - GOOGLE_CLOUD_PROJECT exported (or in .env)
make deploy

# Or one at a time
make deploy-backend
make deploy-frontend
```

The deploy script (`scripts/deploy.sh`) shells out to `gcloud run deploy --source` for each service, wires `PHOENIX_API_KEY` from Secret Manager, and points the frontend at the backend's Cloud Run URL.

## How Phoenix MCP is wired (the load-bearing part)

We mount `@arizeai/phoenix-mcp@latest` directly into ADK as an `McpToolset`, so the QA agent's Gemini calls can invoke Phoenix MCP tools (`list-traces`, `get-spans`, `upsert-prompt`, `add-dataset-examples`, etc.) the same way they invoke our own `FunctionTool`s. See `qa_agent/agent.py` for the binding and `qa_agent/prompt.py` for how the agent is told to use them.

We do NOT wrap Phoenix MCP in our own Python `mcp.ClientSession`. That path was in the original Mystery Shopper scaffold and it was an architectural mistake — it hid the MCP calls inside Python instead of exposing them as the agent's own tool calls. Going through ADK's `McpToolset` is the canonical pattern.

## How tracing is wired

`qa_agent/__init__.py` calls `setup_tracing()` at import time. `setup_tracing()` calls `phoenix.otel.register(project_name=..., auto_instrument=True)` from `arize-phoenix`. The `openinference-instrumentation-google-adk` package picks up the registered tracer and starts producing spans for every ADK call, every Gemini call, and every MCP tool call. Zero per-callsite boilerplate.

Both the QA agent and the SUT trace into the same Phoenix project so a single session view shows the QA agent driving the SUT side-by-side.
