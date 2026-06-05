# Agent - Python service

Backend for the Elastic Apartment Detective. This is the hackathon-safe service
layer that will sit between the frontend and the final Google Cloud + Elastic
integration.

Current status:

- FastAPI service with SSE streaming
- Elastic-specific investigation loop
- Elastic MCP client wrapper
- deterministic demo mode so the product can be built before live data is wired

The current scaffold intentionally avoids non-Google AI tooling. Gemini is the
only model path planned here, and Elastic is the only partner MCP surface.

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

Working now:

- request validation
- SSE event streaming
- listing normalization
- Elastic-oriented tool surface
- sample renter brief generation

Next integration steps:

- replace deterministic planner with Gemini on Vertex AI / Agent Builder
- point the tool client at a real Elastic Agent Builder MCP endpoint
- replace demo data with HPD, 311, and curated tenant-signal indices
- persist `building_briefs` back into Elasticsearch

## Commands

```bash
ruff check src/
mypy src/
pytest
```
