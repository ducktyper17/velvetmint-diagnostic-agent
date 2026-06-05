# Agent Reliability Guard — setup checklist

Owner: human reviewer. Estimated time end-to-end: 90 minutes if Dynatrace tenant is fresh; 30 minutes if a trial already exists.

Every step has a **verification command** and the **expected output** so you can stop at any point if something looks wrong.

## 1. Dynatrace trial tenant

- Sign up: https://www.dynatrace.com/trial/ (15-day free trial, no card required)
- Record the tenant URL once provisioned. Looks like `https://<env-id>.apps.dynatrace.com`.

**Verify:**
```bash
# Open in browser
open "https://<env-id>.apps.dynatrace.com"
```
**Expected:** Dynatrace home loads, logged in.

## 2. MCP gateway URL

The Dynatrace MCP server is reachable at the tenant-scoped gateway:

```
https://<env-id>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp
```

**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://<env-id>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp"
```
**Expected:** `401` (unauthorized without a token — confirms the endpoint exists).

## 3. API token with required scopes

In Dynatrace UI: **Settings > Integration > Platform tokens** > **Generate new token**.

Required scopes (check each):
- `storage:metrics:read`
- `storage:logs:read`
- `storage:events:read`
- `automation:workflows:write`
- `notebooks:write`

Save the token immediately — Dynatrace will not show it again.

**Verify:**
```bash
export DYNATRACE_MCP_TOKEN="<paste-token>"
curl -s -H "Authorization: Bearer $DYNATRACE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
  "https://<env-id>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp" | head -c 200
```
**Expected:** JSON-RPC response containing at least `execute_dql` and `execute_davis_analyzer` in the tool list.

## 4. OTLP HTTP endpoint for the demo app

The refund-assistant uses an OTLP HTTP exporter to push spans into Dynatrace.

- Endpoint: `https://<env-id>.live.dynatrace.com/api/v2/otlp` (note: `.live.`, not `.apps.`)
- Authorization header: `Api-Token <token-with-openTelemetryTrace.ingest-scope>`

You may need a separate ingest token with `openTelemetryTrace.ingest`, `metrics.ingest`, and `logs.ingest` scopes. Generate as in step 3.

Put both in `demo-app/.env`:
```env
OTLP_ENDPOINT=https://<env-id>.live.dynatrace.com/api/v2/otlp
OTLP_HEADERS=Authorization=Api-Token <ingest-token>
```

**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Api-Token <ingest-token>" \
  "https://<env-id>.live.dynatrace.com/api/v2/otlp/v1/traces"
```
**Expected:** `405` (Method Not Allowed for GET — confirms the endpoint accepts auth and exists).

## 5. Verify Davis analyzer names

The Guard defaults to `"Changepoint Agent"` and `"Forecasting Agent"` (see `agent/src/agent/config.py`). These are tenant-dependent.

**Verify in UI:** **Settings > Davis > Analyzers**. Confirm the two display names exist.

**Or via MCP:**
```bash
curl -s -H "Authorization: Bearer $DYNATRACE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_davis_analyzers","arguments":{}},"id":1}' \
  "https://<env-id>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp"
```
**Expected:** JSON list including the two analyzer names. If they differ, override with:
```env
DYNATRACE_CHANGE_ANALYZER_NAME=<actual-changepoint-name>
DYNATRACE_FORECAST_ANALYZER_NAME=<actual-forecast-name>
```

## 6. Local environment files

Create `agent/.env`:
```env
GOOGLE_CLOUD_PROJECT=<your-project-id>
GOOGLE_CLOUD_LOCATION=us-central1
DYNATRACE_ENVIRONMENT_URL=https://<env-id>.apps.dynatrace.com
DYNATRACE_MCP_URL=https://<env-id>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp
DYNATRACE_MCP_TOKEN=<paste-token>
STUB_GEMINI_RESPONSES=false
STUB_DYNATRACE_TOOLS=false
```

For first run with no credentials, set both stubs to `true` — replay mode works fully offline.

Create `frontend/.env.local`:
```env
BACKEND_URL=http://localhost:8080
```

## 7. Install + run locally (3 terminals)

```bash
make setup
```
**Verify:**
```bash
ls agent/.venv && ls demo-app/.venv && ls frontend/node_modules | head -1
```
**Expected:** all three exist.

Terminal 1:
```bash
make demo-app-dev
```
**Verify:** `curl -s http://localhost:8090/healthz` returns `{"status":"ok"}`.

Terminal 2:
```bash
make backend-dev
```
**Verify:** `curl -s http://localhost:8080/healthz` returns `{"status":"ok","version":"0.1.0","environment":"local"}`.

Terminal 3:
```bash
make frontend-dev
```
**Verify:** browser loads `http://localhost:3000` and shows the dashboard.

## 8. Generate before/after telemetry

```bash
make traffic-healthy
```
**Verify:** demo-app logs show 25 successful requests; in the Dynatrace UI **Observe > Distributed traces**, filter by `release_id=release-2026-05-26-baseline` and confirm spans land within ~60 seconds.

```bash
make traffic-bad
```
**Verify:** demo-app logs show 25 requests with retry loops; in Dynatrace, filter by `release_id=release-2026-05-26-bad-prompt` and confirm p95 latency and tokens-per-request are visibly higher than the healthy baseline.

## 9. Run an investigation

Open `http://localhost:3000`, press **Investigate**.

**Verify:**
- The thinking panel streams thoughts, tool calls, and tool results in real time.
- Final report shows summary, probable root cause, impact, and recommended fix.
- Notebook URL is clickable and opens the Dynatrace notebook with the evidence.
- Slack-style notification card appears.

Backup verification (replay mode, no credentials needed):
```bash
cd agent && DEMO_MODE=true uv run pytest tests/test_agent_loop.py -k replay -v
```
**Expected:** `test_run_replay_emits_complete_investigation PASSED`.

## 10. Deploy to Cloud Run

Create the secret once:
```bash
gcloud secrets create dynatrace-mcp-token --replication-policy=automatic
echo -n "<paste-token>" | gcloud secrets versions add dynatrace-mcp-token --data-file=-
```
**Verify:** `gcloud secrets versions list dynatrace-mcp-token` shows one enabled version.

Deploy:
```bash
make deploy
```
**Verify:**
```bash
gcloud run services list --region=us-central1 \
  --format="value(metadata.name,status.url)" \
  | grep -E "(refund-assistant|agent-reliability-guard|reliability-frontend)"
```
**Expected:** three rows, each with a public `https://...run.app` URL.

Smoke-test the hosted backend:
```bash
curl -s "https://<backend-url>/healthz"
```
**Expected:** `{"status":"ok",...}`.

## 11. Record the demo video

- Open the deployed frontend.
- Run `make traffic-healthy` then `make traffic-bad` against the deployed demo-app (or use replay mode).
- Screen-record at 1920x1080, 30fps.
- Follow `VIDEO_SCRIPT.md` beat by beat. Target 2:55.
- Upload to YouTube as **unlisted**. Save the URL.

**Verify:** YouTube link plays in incognito mode (proves it is accessible without your account).

## 12. Submit on Devpost

- Paste the YouTube link into the Devpost video field.
- Paste the hosted frontend URL into the "Try it out" field.
- Paste the GitHub repo URL into the project links.
- Copy the contents of `DEVPOST_DRAFT.md` into the submission narrative.
- Confirm the **Dynatrace** track is selected.
- Confirm the LICENSE in the repo root is **Apache 2.0**.

**Verify:** preview the submission page in a logged-out browser. All three links resolve.

## Final go/no-go

- [ ] Hosted frontend URL responds in <2s.
- [ ] Hosted backend `/healthz` returns 200.
- [ ] Investigation runs end-to-end against the deployed demo-app and produces a notebook.
- [ ] Replay mode runs offline (judge fallback).
- [ ] Video is under 3:00 and uploaded as unlisted.
- [ ] LICENSE is Apache 2.0.
- [ ] Submitted ≥48 hours before deadline.
