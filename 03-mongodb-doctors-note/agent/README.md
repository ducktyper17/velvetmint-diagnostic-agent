# `agent/` — Doctor's Note Decoder service

FastAPI service that powers the Doctor's Note Decoder. Single container,
intended to run on Cloud Run.

> Before reading this file, read [`../LEGAL-DISCLAIMER.md`](../LEGAL-DISCLAIMER.md).
> The agent's framing rules are part of its product behavior, not an
> afterthought.

## What lives here

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app. `POST /decode` and `POST /vault/save`. |
| `extractor.py` | Gemini 3 multimodal call: PDF / image / text → structured medical entities. |
| `retriever.py` | Builds and runs hybrid `$vectorSearch` aggregations against MongoDB Atlas via the official MongoDB MCP server. |
| `responder.py` | Synthesizes the final `DecodedReport` from entities + retrieval. Defines the Pydantic response schema. |
| `prompts.py` | System prompt and few-shots. Hard-bakes the "explain, do not diagnose" framing. Loads disclaimer text from `../LEGAL-DISCLAIMER.md`. |
| `seed_data.py` | One-shot script that seeds the Atlas knowledge base with a handful of sample documents (literature, guidelines, forum). |
| `pyproject.toml` | Dependencies. Real package names; versions are pinned where confidently known and marked `TODO confirm` where not. |
| `.env.example` | Environment variables required at runtime. Copy to `.env`. |

## Prerequisites

- Python 3.11+
- A MongoDB Atlas project with at least one cluster (the free M0 tier
  is fine for the demo). Vector Search is available on M0 as of 2024.
- A Voyage AI API key (`VOYAGE_API_KEY`). Voyage's `voyage-3-large` is
  the current default; check whether the `voyage-medical` domain model
  is generally available at build time and prefer it if so.
- A Google Cloud project with Vertex AI enabled and a service account
  that can call Gemini 3 models.
- Node.js 20+ on the host **only if** running the MongoDB MCP server
  locally over stdio (the official server is distributed as an npm
  package; see the MongoDB docs). For Cloud Run we bundle the MCP
  server binary into the image.

## Local setup

```bash
# from this directory
cp .env.example .env
# Fill in MONGODB_URI, MONGODB_DB, VOYAGE_API_KEY, GOOGLE_CLOUD_PROJECT,
# GOOGLE_CLOUD_LOCATION, GEMINI_MODEL, MCP_SERVER_CMD.

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Seeding the knowledge base

```bash
python seed_data.py
```

This script:

1. Connects to Atlas with `pymongo` (used only for index bootstrap; the
   request path uses MCP, not raw pymongo).
2. Creates the database, collections, and Vector Search indexes if they
   do not already exist.
3. Inserts a few sample documents into `literature`, `guidelines`, and
   `forum_posts`, all clearly labeled `is_sample: true`.
4. Triggers Voyage AI embedding generation by going through the MCP
   server's `insert-many` tool when `VOYAGE_API_KEY` is set; falls back
   to a no-embedding insert otherwise (vector search will not work
   until embeddings are present).

Re-running the script is safe: it upserts on a deterministic `_id`.

## Running the service

```bash
uvicorn main:app --reload --port 8080
```

Then:

```bash
# Pasted text path
curl -X POST http://localhost:8080/decode \
  -H 'Content-Type: application/json' \
  -d '{"text": "TIRADS 3 nodule, right thyroid lobe, 2.1 cm, mixed echogenicity, no microcalcifications. Recommend follow-up ultrasound in 12 months."}'

# Multipart file upload path (PDF or image)
curl -X POST http://localhost:8080/decode \
  -F 'file=@/path/to/sample_report.pdf'
```

The response is a `DecodedReport` JSON object. Every response includes
the full disclaimer block. If the disclaimer field is missing or empty,
the server returns HTTP 500 by design.

## Tests

> Not in scope for the backup scaffold. We have left obvious seams
> (extractor / retriever / responder are independently testable pure
> functions over their inputs) so that adding `pytest` later is
> mechanical.

## Deploy to Cloud Run (one-liner once GCP project is set up)

```bash
gcloud run deploy doctors-note \
  --source . \
  --region us-central1 \
  --service-account doctors-note-runtime@$PROJECT.iam.gserviceaccount.com \
  --set-secrets MONGODB_URI=mongo-uri:latest,VOYAGE_API_KEY=voyage:latest
```

## Operational notes

- The MCP server is launched as a subprocess from `main.py`'s startup
  hook. If it dies, the next `/decode` request fails fast with a 503
  rather than silently retrying.
- Vertex AI calls are not retried automatically; the responder is
  stateless and the client should retry idempotently.
- We log the model versions of Gemini and Voyage on every response (in
  `metadata`) so retroactive audit is possible without surfacing PHI.
