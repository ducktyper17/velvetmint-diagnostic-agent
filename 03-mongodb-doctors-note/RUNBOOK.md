# Runbook — Doctor's Note Decoder (MongoDB track)

Everything engineering-side is done, tested, and committed. This is the
exact, ordered path from here to a submitted MongoDB-track entry. Steps 1–4
need your credentials/accounts; nothing here is optional for submission.

## 0. One-time prereqs

- A MongoDB Atlas cluster (free M0 is fine) with a database user and your
  IP / 0.0.0.0/0 allow-listed.
- A GCP project with billing on and these APIs enabled:
  `aiplatform`, `run`, `secretmanager`, `cloudbuild`.
- **Confirm Gemini 3 access:** in the GCP console, open Vertex AI → Model
  Garden and verify `gemini-3.1-pro-preview` is available in your region.
  (The hackathon requires Gemini 3. `gemini-3-pro-preview` was retired
  2026-03; we default to `gemini-3.1-pro-preview`.)

## 1. Local live run (~30 min)

```bash
cd 03-mongodb-doctors-note/agent
source .venv/bin/activate            # already created
# Edit .env: set MONGODB_URI and GOOGLE_CLOUD_PROJECT to real values.
gcloud auth application-default login # gives Vertex local credentials

python scripts/ingest_pubmed.py --per 8  # pull REAL PubMed abstracts (no creds needed)
python seed_data.py                  # embeds the corpus + builds Atlas vector indexes
# Wait ~1 min for the Atlas index to finish building (status in Atlas UI).
# (seed_data prefers corpus/literature.json if present; a real one is already
#  committed, so this step ships real literature out of the box.)

uvicorn main:app --port 8080
# Open http://localhost:8080, click "Try: thyroid ultrasound", Explain.
```

Success = the result card fills in AND the right-hand "Knowledge base" panel
shows real Atlas hits (literature / guidelines / patient experiences), not
the built-in fallback. Check `metadata.fallback` is absent in the response.

### If retrieval shows the fallback bundle
- Atlas index still building, or `VERTEX_EMBEDDING_DIM` (3072) doesn't match
  the index dimension → re-run `seed_data.py` after the index reports ready.
- MCP couldn't reach Atlas → check the `MONGODB_URI` and Atlas IP allowlist.

## 2. Deploy to Cloud Run → hosted URL (~30–45 min)

```bash
# Put the Atlas URI in Secret Manager once:
printf '%s' '<your full mongodb+srv URI>' \
  | gcloud secrets create MONGODB_URI --data-file=- --replication-policy=automatic

cd 03-mongodb-doctors-note
./scripts/deploy.sh          # prints the public hosted URL when done
```

Open the printed URL, run the same sample, confirm Atlas hits appear. This
URL is what goes in the Devpost "Try it" field.

## 3. Record the demo video (~half day)

Use [demo-script.md](./demo-script.md). Non-negotiables:
- Keep the lower-third disclaimer band visible the entire video.
- On screen, show: the report going in → the Atlas retrieval panel → the
  plain-language explanation with the three questions.
- Show the `$vectorSearch` aggregation once (the differentiator) — the
  pipeline is in `retriever.build_pipeline`.
- Keep it under 3:00.

## 4. Submit on Devpost

- Paste [DEVPOST_DRAFT.md](./DEVPOST_DRAFT.md) into the Devpost fields.
- Public repo URL: the current monorepo remote is
  `github.com/ducktyper17/velvetmint-diagnostic-agent`. Either submit that
  (note in the description which folder is this project) or push a clean
  copy of `03-mongodb-doctors-note/` to a repo named for this project.
- Hosted URL: the Cloud Run URL from step 2.
- Video URL: from step 3.

## What's intentionally out of scope for the demo
- `/vault/save` is a stub (static token, no real auth) — saved history is a
  "what's next," not part of the core demo.
- Corpus is 4 conditions of clearly-labeled sample data. Enough to show the
  hybrid retrieval; not a production knowledge base.
