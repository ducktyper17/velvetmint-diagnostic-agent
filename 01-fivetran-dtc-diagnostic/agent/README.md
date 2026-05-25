# Agent — Python service

The DTC Brand Health Diagnostic Agent's backend. FastAPI + a ReAct-style
loop that calls Gemini 3 (via Vertex AI) and the Fivetran MCP server.

This README covers local development. Deployment to Cloud Run is in
[`../infra/README.md`](../infra/README.md).

## Layout

```
agent/
├── README.md            (this file)
├── pyproject.toml       (Python 3.11, hatch build backend)
├── .env.example         (every env var, with descriptions)
└── src/agent/
    ├── __init__.py
    ├── main.py                FastAPI app + uvicorn entrypoint
    ├── agent_loop.py          ReAct loop
    ├── tools.py               Fivetran MCP client + tool wrappers
    ├── prompts.py             System prompt + few-shots
    ├── diagnostic_engine.py   BigQuery analytical battery
    └── config.py              pydantic-settings config
```

## Prerequisites

- Python 3.11 (3.12 also works; 3.13 not yet supported by all dependencies)
- A Fivetran trial with API key + secret
- A GCP project with Vertex AI + BigQuery enabled
- A MongoDB Atlas cluster (free M0 tier is plenty)
- The Fivetran MCP server running locally or on Cloud Run
  (https://github.com/fivetran/fivetran-mcp)

## First-time setup

```bash
# 1. Clone and enter
cd agent

# 2. Virtualenv + install
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Config
cp .env.example .env
# edit .env to fill in:
#   GOOGLE_CLOUD_PROJECT
#   GOOGLE_APPLICATION_CREDENTIALS  (path to a service-account key JSON)
#   FIVETRAN_MCP_URL                (where the MCP is running)
#   FIVETRAN_MCP_TOKEN              (bearer token you generate)
#   MONGODB_URI

# 4. (Optional) authenticate gcloud so BigQuery client picks up app default creds
gcloud auth application-default login
```

## Running the Fivetran MCP server alongside

The agent talks to the MCP via HTTP. The simplest local layout is two
shells, one per service:

```bash
# Shell 1 — MCP
git clone https://github.com/fivetran/fivetran-mcp.git
cd fivetran-mcp
# follow that repo's README; set:
#   FIVETRAN_API_KEY=...
#   FIVETRAN_API_SECRET=...
#   FIVETRAN_ALLOW_WRITES=true
# then start in HTTP transport mode on port 3333

# Shell 2 — agent
cd agent
source .venv/bin/activate
dtc-agent
# or, equivalently:  uvicorn agent.main:app --reload --port 8080
```

## Smoke-testing it

Once both processes are up:

```bash
# Liveness
curl http://localhost:8080/healthz

# Kick off a diagnosis. The response is an SSE stream — `-N` disables curl's
# output buffering so you see events as they arrive.
curl -N -X POST http://localhost:8080/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "question": "why is my revenue down 22% this month?",
    "brand_id": "velvetmint"
  }'
```

You should see lines like:

```
event: thought
data: {"iteration":0,"text":"Starting diagnosis...","conversation_id":"..."}

event: thought
data: {"iteration":1,"text":"Plan: pull data from every channel..."}

event: tool_call
data: {"iteration":1,"name":"setup_connector","args":{"source":"shopify"}}

event: tool_result
data: {"iteration":1,"name":"setup_connector","result":{...}}

event: final_report
data: {"iteration":2,"findings":[...]}

event: done
data: {"iteration":2,"reason":"finalize_diagnosis"}
```

Until the Gemini and MCP integrations are wired (Days 2 and 3 of the
[build plan](../build-plan.md)), the loop returns a deterministic stub that
exercises the SSE plumbing end-to-end.

## Tests

```bash
pytest                      # unit tests
pytest -k diagnose -v       # only the /diagnose path
ruff check src/             # lint
mypy src/                   # type check
```

## What needs filling in (TODO map)

The scaffold runs end-to-end, but several integration points are stubbed
with clearly marked `TODO` comments:

| File | What's stubbed | When it lands |
|---|---|---|
| `agent_loop.py::_call_gemini` | The Vertex AI Gemini 3 call | Day 2 |
| `tools.py::FivetranMCPClient.call_tool` | Confirm endpoint path / SSE behavior | Day 3 |
| `tools.py::_iter_connections` / `_extract_connection_id` | Parse real MCP responses | Day 3 |
| `main.py` lifespan | MongoDB client open/close | Day 5 |
| `main.py::diagnose` | Persist events to MongoDB | Day 5 |
| `main.py::get_diagnosis` | Read diagnosis from MongoDB | Day 5 |
| `diagnostic_engine.py::run_named_query` | Real BigQuery queries | Day 7 |
| `agent_loop.py::_resolve_destination_id` / `_resolve_group_id` | MongoDB-backed brand registry | Day 12 |

See `../SCAFFOLD-NOTES.md` for the consolidated stub list with effort estimates.

## Coding standards

- Python 3.11 type hints everywhere; ``from __future__ import annotations``.
- ``ruff`` + ``mypy --strict`` on the package; CI gates on both.
- Use ``structlog`` for logs (already a dependency); never ``print``.
- Secrets always wrapped in ``pydantic.SecretStr`` so they cannot leak into
  exception messages.
- One concept per module; no "utils.py" dumping ground.
