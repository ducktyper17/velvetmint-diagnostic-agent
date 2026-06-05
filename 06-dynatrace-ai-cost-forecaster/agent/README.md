# Agent Reliability Guard - Python service

The Dynatrace track backend. FastAPI + a ReAct-style investigation loop that
will call Gemini on Google Cloud and the Dynatrace MCP server.

This service is the local/dev backend for the submission. The hackathon
requirements still apply: the final project must use Gemini, Google Cloud Agent
Builder / Agent Platform, and the Dynatrace MCP server.

## Layout

```text
agent/
|- README.md
|- pyproject.toml
|- .env.example
\- src/agent/
   |- __init__.py
   |- main.py          FastAPI app + SSE endpoint
   |- agent_loop.py    ReAct-style investigation loop
   |- tools.py         Dynatrace MCP client + typed tool wrappers
   |- prompts.py       System prompt + few-shot traces
   \- config.py        pydantic-settings config
```

## What this service does

Given a request like:

> "Investigate why the refund assistant got slower and more expensive after the
> last release."

the service will:

1. query Dynatrace runtime telemetry
2. run change analysis / forecasting tools
3. summarize the probable root cause
4. create a Dynatrace notebook
5. send an operator-facing notification

The current scaffold keeps the Gemini and Dynatrace integrations clearly marked
with TODOs while returning deterministic stub responses so the SSE flow can be
tested end to end.

## Prerequisites

- Python 3.11
- A Google Cloud project with Vertex AI enabled
- Access to Google Cloud Agent Builder / Agent Platform
- A Dynatrace tenant or trial environment
- Access to the Dynatrace MCP server (remote or local gateway)

## First-time setup

```bash
cd agent

uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -e ".[dev]"

cp .env.example .env
# fill in:
#   GOOGLE_CLOUD_PROJECT
#   DYNATRACE_ENVIRONMENT_URL
#   DYNATRACE_MCP_URL
#   DYNATRACE_MCP_TOKEN
```

For the remote Dynatrace MCP gateway, `DYNATRACE_MCP_URL` should be the full MCP
endpoint, for example:

```text
https://YOUR_ENV.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp
```

Authenticate to Google Cloud locally with ADC:

```bash
export CLOUDSDK_CONFIG="$HOME/.local/share/gcloud-config"
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## Running locally

```bash
cd agent
source .venv/bin/activate
reliability-guard
```

Equivalent `uvicorn` command:

```bash
uvicorn agent.main:app --reload --port 8080
```

## Smoke test

```bash
curl http://localhost:8080/healthz

curl -N -X POST http://localhost:8080/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Investigate why refund-assistant got slower after release 2026-05-26.",
    "service_name": "refund-assistant",
    "release_id": "release-2026-05-26",
    "lookback_minutes": 180
  }'
```

You should see SSE events like:

```text
event: thought
data: {"iteration":0,"text":"Starting investigation...","conversation_id":"..."}

event: tool_call
data: {"iteration":1,"name":"query_runtime_signals","args":{...}}

event: tool_result
data: {"iteration":1,"name":"query_runtime_signals","result":{...}}

event: final_report
data: {"iteration":5,"summary":"...","recommended_fix":"..."}

event: done
data: {"iteration":5,"reason":"finalize_investigation"}
```

## Tests

```bash
pytest
pytest -k healthz -v
python scripts/smoke_gemini.py
python scripts/smoke_dynatrace_mcp.py
python scripts/smoke_investigate.py
```

Copy `.env.example` → `.env` and map secrets from `00-shared/SECRET-MAP.md` before
running the Dynatrace smoke script. Set `SMOKE_RUN_DQL=true` to also run a tiny
`execute_dql` query (may incur Grail scan costs).

## TODO map

| File | What is stubbed now | When it lands |
|---|---|---|
| `agent_loop.py::_call_gemini` | Prompt and tool schemas still need tuning against real traces | next integration pass |
| `tools.py::*` wrappers | Some Dynatrace tool argument shapes still use fallback guesses until verified against a live tenant | next integration pass |
| `main.py::get_investigation` | Persistence / replay store | later |

## Guardrails from the hackathon rules

- Gemini only for agent reasoning; no OpenAI, Anthropic, or other non-Google AI.
- Dynatrace MCP is the required partner integration, not optional decoration.
- Host on Google Cloud, not AWS or Azure.
- Keep the core flow centered on Agent Builder / Agent Platform.
