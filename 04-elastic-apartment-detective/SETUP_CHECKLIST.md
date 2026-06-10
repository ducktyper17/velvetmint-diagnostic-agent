# Apartment Detective — setup checklist

Owner: human reviewer. End-to-end estimate: **15 minutes for the offline demo**
(no accounts), **60 minutes for the fully live path** (fresh Elastic + GCP).

Every step has a **verification command** and **expected output** so you can stop
at any point if something looks wrong.

---

## Path A — Offline demo (no credentials, 15 min)

This runs the entire product end-to-end with seeded data and a deterministic
planner. Perfect for reviewers and for recording the video.

### A1. Backend

```bash
cd agent
python3.11 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
cp .env.example .env            # defaults already have DEMO_MODE=true, STUB_GEMINI_RESPONSES=true
./.venv/bin/uvicorn agent.main:app --reload --port 8080 --app-dir src
```

**Verify:**
```bash
curl -s http://localhost:8080/healthz
```
**Expected:** `{"status":"ok",...,"demo_mode":true}`

### A2. Frontend (second terminal)

```bash
cd frontend
npm install
BACKEND_URL=http://localhost:8080 npm run dev
```

**Verify:** open http://localhost:3000, press **Investigate** with the prefilled
123 Orchard St link.
**Expected:** five tool calls stream in one batch, the evidence strip fills
(5 violations / 18 complaints / 61% / 1.7×), and a **9.8/10** risk brief appears.

### A3. One-command smoke (optional)

```bash
cd agent && ./.venv/bin/python scripts/smoke_investigate.py
```
**Expected:** the full thought → tool → brief stream prints, ending with
`★ risk 9.8/10`.

### A4. Tests

```bash
cd agent && ./.venv/bin/pytest -q
```
**Expected:** `7 passed`.

---

## Path B — Fully live (Gemini + Elastic, ~60 min)

### B1. Elastic Cloud Serverless project

- Create a free Serverless project at https://cloud.elastic.co (or via Google Cloud Marketplace). Requires Elastic 9.2+ for Agent Builder.
- Note the project endpoint, e.g. `https://<project>.es.<region>.elastic.cloud:443`.

**Verify:** the Kibana home loads and **Agent Builder** appears in the menu.

### B2. Provision indices + load data

```bash
cd agent && ./.venv/bin/pip install -e ".[ingest]"
export ELASTIC_ENDPOINT="https://<project>.es.<region>.elastic.cloud:443"
export ELASTIC_API_KEY="<api key with manage privileges>"
./.venv/bin/python scripts/elastic_setup.py        # creates the 4 indices
./.venv/bin/python scripts/ingest_nyc.py --zips 10002,10009   # real HPD + 311
./.venv/bin/python scripts/seed_tenant_signals.py  # curated tenant corpus (ELSER)
```
**Expected:** `+ created hpd_violations ...`, then `indexed N` lines for each loader.

### B3. Build the six Agent Builder tools

In Kibana → **Agent Builder → Tools**, create the six tools exactly as specified
in [`elastic/agent_builder_tools.md`](elastic/agent_builder_tools.md) (use the
tool ids verbatim — the agent calls them by name). Then copy the **MCP endpoint
URL** shown in the Tools UI.

**Verify:** in Agent Builder, run `get_hpd_violations` with `address="123 Orchard
St"` — it returns rows.

### B4. MCP API key

Create an API key with `agentBuilder:read` + read on the four indices.

**Verify:**
```bash
curl -s -X POST "<ELASTIC_MCP_URL>" \
  -H "Authorization: ApiKey <key>" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | head -c 300
```
**Expected:** JSON listing your six tools.

### B5. Google Cloud / Vertex AI

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=<project>
cd agent && ./.venv/bin/python scripts/smoke_gemini.py
```
**Expected:** `OK gemini-2.5-flash: 'ONLINE'`

### B6. Flip to live and run

In `agent/.env` set:
```
DEMO_MODE=false
STUB_GEMINI_RESPONSES=false
ELASTIC_MCP_URL=<from B3>
ELASTIC_MCP_API_KEY=<from B4>
GOOGLE_CLOUD_PROJECT=<your project>
```
Then run the live MCP smoke test:
```bash
cd agent && ./.venv/bin/python scripts/smoke_elastic_mcp.py
```
**Expected:** the tool list plus a real result line for each of the five reads.

---

## Path C — Deploy to Cloud Run

```bash
gcloud secrets create elastic-mcp-api-key --data-file=- <<< "<key>"
./scripts/deploy.sh all
```
**Expected:** two services printed — `apartment-detective-backend` and
`apartment-detective-frontend` — each with an HTTPS URL. Open the frontend URL.

---

## Rules compliance (Google Cloud Rapid Agent Hackathon)

- **AI provider:** Gemini on Vertex AI only. No OpenAI/Anthropic/Cohere/Voyage. ELSER (Elastic's own model) handles semantic search — no third-party embeddings.
- **Partner MCP:** Elastic Agent Builder MCP is the agent's sole tool surface and is genuinely load-bearing (ES|QL + ELSER + memory writeback).
- **Required stack:** Google Cloud (Vertex AI + Cloud Run) + Gemini + one partner MCP. ✓
- **License:** Apache-2.0.
