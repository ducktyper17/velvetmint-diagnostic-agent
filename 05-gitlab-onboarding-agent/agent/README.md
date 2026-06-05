# Agent — Blast Radius backend

Python service for the GitLab-track zero-day response demo.

The goal of this scaffold is to make the hackathon story runnable early:
- receive a vulnerability event
- inspect a small service catalog
- identify affected GitLab projects
- open incident and patch actions through a GitLab MCP-shaped client
- stream reasoning and actions back to the UI

The current version is intentionally **demo-first**:
- the incident flow is deterministic
- the GitLab MCP client is stubbed in `demo_mode`
- the Gemini / Agent Builder handoff is prepared but not wired yet

This is still the right first build step because the hackathon judging happens on
the visible agent loop and the quality of the end-to-end product, not on how
early we reached full live integrations.

## Layout

```text
agent/
├── README.md
├── pyproject.toml
├── .env.example
├── src/agent/
│   ├── __init__.py
│   ├── agent_loop.py
│   ├── config.py
│   ├── main.py
│   ├── prompts.py
│   ├── scenario.py
│   └── tools.py
└── tests/
    └── test_agent_loop.py
```

## API

- `GET /healthz` returns service health
- `POST /incidents/analyze` streams SSE events:
  - `thought`
  - `tool_call`
  - `tool_result`
  - `final_report`
  - `done`

## First-time setup

```bash
cd agent
uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env
blast-radius-agent
```

## Smoke test

```bash
curl http://localhost:8080/healthz

curl -N -X POST http://localhost:8080/incidents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "incident_title": "Critical log4js vulnerability",
    "cve_id": "CVE-2026-4242",
    "vulnerable_package": "log4js",
    "fixed_version": "6.9.1"
  }'
```

## Hackathon compliance notes

- Reasoning layer is reserved for **Gemini + Google Cloud Agent Builder**
- Partner actions are shaped around the **official GitLab MCP server**
- Hosting target is **Cloud Run**
- Secrets belong in **Secret Manager** for deployed environments
- The deployment path is intended to go through **GitLab CI/CD -> Artifact Registry -> Cloud Run**

## Implemented

- SSE incident workflow (`POST /incidents/analyze`)
- Blast-radius scoring and demo service catalog
- GitLab MCP HTTP client with automatic demo fallback
- Grounding docs in `data/` (service catalog + runbooks)
- Gemini executive summary via Vertex AI (`USE_GEMINI_SUMMARY=true`)
- Dashboard UI at `/`

## Optional polish

- Live GitLab MCP OAuth against a real group
- Persist incidents for replay (`GET /incidents/{id}`)
- Full Gemini-planned tool selection (today: deterministic orchestration + Gemini summary)
