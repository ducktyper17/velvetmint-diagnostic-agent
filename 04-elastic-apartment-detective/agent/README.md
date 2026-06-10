# Agent - Python service

Backend for the Elastic Apartment Detective. This is the hackathon-safe service
layer that will sit between the frontend and the final Google Cloud + Elastic
integration.

Current status:

- FastAPI service with SSE streaming
- ReAct investigation loop around Gemini 2.5 Flash on Vertex AI (forced
  function-calling; five read tools fanned out concurrently in one turn)
- Elastic Agent Builder MCP client with response-envelope normalization
- two independent offline switches so the product runs with no credentials:
  - `DEMO_MODE` — Elastic tools return seeded sample payloads
  - `STUB_GEMINI_RESPONSES` — deterministic planner instead of a Gemini call
- `run_replay` — paced, deterministic stream for a bulletproof live demo

Gemini is the only model path and Elastic is the only partner MCP surface — no
non-Google AI tooling, per the hackathon rules.

## Layout

```text
agent/
├── README.md
├── pyproject.toml
├── .env.example
└── src/agent/
    ├── __init__.py
    ├── config.py
    ├── prompts.py
    ├── tools.py
    ├── agent_loop.py
    └── main.py
```

## First-time setup

```bash
cd agent
uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -e ".[dev]"

cp .env.example .env
```

## Local run

```bash
source .venv/bin/activate
apartment-detective-agent
```

Or:

```bash
uvicorn agent.main:app --reload --port 8080
```

## Smoke test

```bash
curl http://localhost:8080/healthz

curl -N -X POST http://localhost:8080/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "listing_url": "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002"
  }'
```

The response is an SSE stream. In demo mode, the loop emits deterministic
Elastic-style tool calls and returns a renter-risk brief for a seeded address.

## What is real vs stubbed

Working now (offline, no credentials):

- request validation + SSE event streaming
- listing normalization (with demo-address snapping)
- the full ReAct loop: plan → five parallel reads → save brief → finalize
- grounded risk scoring from tool outputs
- seeded sample payloads for every Elastic tool

Flip to live by setting `DEMO_MODE=false` + `STUB_GEMINI_RESPONSES=false` and
providing `ELASTIC_MCP_URL`, `ELASTIC_MCP_API_KEY`, and `GOOGLE_CLOUD_PROJECT`:

- the planner becomes a real Gemini-on-Vertex tool-calling loop
- the tool client hits the Elastic Agent Builder MCP endpoint
- evidence comes from the `hpd_violations`, `nyc_311`, and `tenant_signal_docs`
  indices (provision with `scripts/elastic_setup.py`, load with
  `scripts/ingest_nyc.py` + `scripts/seed_tenant_signals.py`)
- `save_building_brief` persists to the `building_briefs` index

See `../SETUP_CHECKLIST.md` (Path B) and `../elastic/agent_builder_tools.md`.

## Scripts

```bash
python scripts/smoke_investigate.py     # full stream in-process (offline)
python scripts/smoke_gemini.py          # verify Vertex AI access
python scripts/smoke_elastic_mcp.py     # verify live MCP tools (DEMO_MODE=false)
python scripts/elastic_setup.py         # create the 4 indices
python scripts/ingest_nyc.py            # load real HPD + 311 from NYC Open Data
python scripts/seed_tenant_signals.py   # seed the ELSER tenant corpus
```

## Commands

```bash
ruff check src/
mypy src/
pytest
```
