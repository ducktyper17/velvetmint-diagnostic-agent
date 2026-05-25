# agent/

Python service that runs the Mystery Shopper audit loop.

## What lives here

| File | Role |
|---|---|
| `main.py` | FastAPI app. Exposes `/audit`, `/audit/{id}`, `/audit/{id}/report`. |
| `scenarios.py` | Curated test-scenario data classes. Ten ship in the scaffold; fifty in the final dataset. |
| `judge.py` | LLM-as-judge runner. One Phoenix experiment row per (scenario, dimension). |
| `prompts.py` | Versioned judge prompts for the six scoring dimensions. |
| `pyproject.toml` | Dependencies. |
| `.env.example` | Required environment variables with descriptions. |

What's intentionally *not* here yet:

- The Gemini 3 / Vertex AI orchestrator loop. The skeleton calls out the integration points; the real client wiring is a `TODO` block.
- The Phoenix MCP client wiring. Same — interface is sketched, the actual `mcp.ClientSession` connection is a `TODO`.
- Target-AI adapters. There's a `_send_to_target` stub; only the HTTPS-chat adapter will exist in the MVP.
- The report renderer. The report data structure is defined, but the HTML template is post-scaffold work.

The scaffold is meant to be runnable end-to-end against in-memory fakes within roughly one day of additional work — see `../SCAFFOLD-NOTES.md` for the remaining-work estimate.

## Local setup

This project targets Python 3.11+.

```bash
cp .env.example .env
# fill in GOOGLE_CLOUD_PROJECT, PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT, etc.

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Authentication for Vertex AI uses Application Default Credentials. If you're running locally:

```bash
gcloud auth application-default login
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
```

## Run

```bash
uvicorn main:app --reload --port 8080
```

Smoke-test the API once it's up:

```bash
curl -X POST http://localhost:8080/audit \
  -H 'content-type: application/json' \
  -d '{
    "targets": [
      {"name": "Marriott", "kind": "http", "endpoint": "https://example.com/chat"}
    ],
    "scenario_set": "default-10"
  }'
```

The response is a job id; poll `GET /audit/{id}` for status.

## Deploy to Cloud Run (post-scaffold)

A `Dockerfile` and `gcloud run deploy` invocation will land alongside the first real Gemini call. The plan:

```bash
gcloud run deploy mystery-shopper \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets PHOENIX_API_KEY=phoenix-api-key:latest \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
```

## How the Phoenix integration is split

We use Phoenix two different ways on purpose:

- **OTel tracing** (the Python SDK) for every per-turn span during a scenario run. This path is hot; an MCP round-trip per span would be wasteful.
- **MCP tools** (the `mcp` Python client talking to `@arizeai/phoenix-mcp`) for everything that is conceptually "data plane on Phoenix" — datasets, experiments, judge-prompt versions. These are infrequent, and going through MCP means the same operations the agent does are also doable from the Phoenix UI by a reviewer.

`judge.py` and the orchestrator loop are where the MCP client is used. Tracing is configured once at startup in `main.py`.
