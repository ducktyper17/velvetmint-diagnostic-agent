# Google Cloud Rapid Agent Hackathon — Workspace

**Deadline:** June 11, 2026 (Thu, 2:00 PM PDT) — hard cutoff
**Judging:** June 22 – July 6, 2026 (our hosted demo URL must stay up during this window)
**Prize per track:** $5K / $3K / $2K
**Total tracks:** 6 — Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace

**Hard requirements** (from the [official rules](https://rapid-agent.devpost.com/rules)):
1. Functional agent **powered by Gemini and Google Cloud Agent Builder**
2. Integrates one **partner MCP server** (Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace)
3. **No non-Google AI tools allowed** (no Claude, no OpenAI, no Cohere) — only Gemini + partner-built-in AI features
4. Hosted URL + public OSI-licensed repo + ≤3-min YouTube/Vimeo demo video

See `00-shared/hackathon-rules.md` for the full canonical rules with citations.

## Strategy

We're shipping **two feature-complete submissions** into two different low-competition tracks (Arize + Dynatrace). The math: 18 total prize slots (3 per track × 6 tracks); two submissions = two independent shots at the pool. The other 4 tracks (Fivetran, MongoDB, Elastic, GitLab) are explicitly out-of-scope after the May 28 reset — each was either a crowded track, a generic concept, or a build with trial-expiry risk.

This workspace contains:

- **Primary submission** — `02-arize-mystery-shopper/` — Self-Improving QA Agent. Feature-complete in code; needs Phoenix Cloud credentials + Vertex AI + a `make seed && make run-loop` pass to bring online.
- **Secondary submission** — `06-dynatrace-ai-cost-forecaster/` — Agent Reliability Guard. Feature-complete in code; needs a Dynatrace tenant + MCP gateway URL + token to bring online. Stub mode lets it run end-to-end without those.
- **Backup / discarded** — `01-fivetran-dtc-diagnostic/`, `03-mongodb-doctors-note/`, `04-elastic-apartment-detective/`, `05-gitlab-onboarding-agent/` — preserved for git history but not on the critical path.

## Primary pick

**Arize track — Self-Improving QA Agent.**

> *"The AI quality engineer that never sleeps."*

A code-owned Gemini ADK agent that owns the entire eval methodology for a customer-support AI. It:

1. Pulls a versioned 50-scenario test set from a **Phoenix dataset**.
2. Runs each scenario against a **Subject Under Test (SUT)** — a deliberately-flawed Gemini customer-support agent for our fake DTC brand (reusing `synthetic-data/`).
3. Auto-instruments every turn into Phoenix via `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)`.
4. Runs a **Phoenix LLM-as-judge experiment** across six dimensions (empathy, accuracy, escalation, bias, hallucination, brand voice). Judge model is Gemini 2.5 (per hackathon AI rules).
5. **The self-improvement loop (the demo moment).** The QA agent calls **Phoenix MCP at runtime** to read its own failure spans (`list-traces`, `get-spans`, `get-experiment-by-id`), clusters failures by mode, proposes a system-prompt rewrite for the SUT, `upsert-prompt`s the new version into Phoenix, re-runs the experiment, and shows the score delta — live, in front of the judges.
6. Newly-discovered failure modes are written back to the Phoenix dataset via `add-dataset-examples`. The test suite grows over time.

**Why this:**

1. **Arize literally told us this is how they'll score it.** Their partner page calls out "quality of the agent's self-improvement loop" and "bonus points for agents that use their own observability data to improve over time" as explicit criteria. Our scaffold is the most direct expression of those words.
2. **Phoenix MCP is genuinely load-bearing in both directions** — read (introspection) and write (mutating prompts and growing datasets). That's the engineering depth the Tech tiebreaker rewards.
3. **No trial-expiry risk.** Phoenix Cloud free tier is permanent.
4. **No TOS risk.** We audit our own deployed agent, not competitors.
5. **Reuses existing work.** The `synthetic-data/` DTC corpus becomes the SUT's domain (it's a customer-support agent for the fake VelvetMint brand). Zero waste from the Fivetran-era build.

See `DECISION.md` for the full A/B/C ranking with judge grades and the May 26 changelog explaining the pivot from Fivetran.

## Folder map

| Folder | Status | Idea |
|---|---|---|
| `02-arize-mystery-shopper/` | **Primary — feature-complete in code** | Self-Improving QA Agent. ADK + Phoenix MCP read+write + 30 scenarios × 6 Gemini judges × 3 replicas + Next.js frontend + Dockerfiles + Cloud Run deploy |
| `06-dynatrace-ai-cost-forecaster/` | **Secondary — feature-complete in code** | Agent Reliability Guard. Gemini ReAct loop + Dynatrace MCP (DQL + Davis analyzers + notebooks + Slack) + OTel-instrumented refund-assistant + Next.js frontend + Dockerfiles + Cloud Run deploy |
| `01-fivetran-dtc-diagnostic/` | Discarded | DTC brand health root-cause agent (trial expires June 7) |
| `03-mongodb-doctors-note/` | Discarded | Hybrid retrieval; crowded track + legal-risk framing |
| `04-elastic-apartment-detective/` | Discarded | Generic listing search; crowded track |
| `05-gitlab-onboarding-agent/` | Discarded | Most crowded track (500+ submissions expected) |
| `00-shared/` | — | MCP cheatsheets, GCP stack, hackathon rules, judging rubric |
| `synthetic-data/` | ✅ Done | Story-driven fake DTC dataset — context for the Arize SUT |

## What you need to do today

The code is complete for both submissions. Outstanding work is environment setup + a live shakedown run + the videos.

### Arize (primary)

1. **Phoenix Cloud account** at <https://app.phoenix.arize.com> (free, instant) → get `PHOENIX_API_KEY` (format `px_live_...`).
2. **Phoenix space URL** — copy `Hostname` from Phoenix → Settings (includes `/s/<your-space>`) into `PHOENIX_COLLECTOR_ENDPOINT`. Bare `app.phoenix.arize.com` will 401.
3. **GCP project + Vertex AI enabled** + `gcloud auth application-default login`.
4. **Node 18+ on PATH** (Phoenix MCP runs via `npx @arizeai/phoenix-mcp@latest`).
5. `cd 02-arize-mystery-shopper/agent && make setup && make seed && make run-loop` → produces `out/delta_report.json`.
6. `cd ../frontend && npm install && npm run dev` (with backend at `make dev` in a second terminal) → live at <http://localhost:3000>.
7. When green: `make deploy` (after creating `phoenix-api-key` secret in Secret Manager).

### Dynatrace (secondary)

1. **Dynatrace tenant** (free trial at <https://www.dynatrace.com/trial/>) + MCP gateway URL (`https://<env>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp`) + token.
2. **OTLP endpoint + Authorization** for the demo-app to send traces to Dynatrace.
3. `cd 06-dynatrace-ai-cost-forecaster && make setup` then run `demo-app-dev`, `backend-dev`, `frontend-dev` in three terminals.
4. Run `cd demo-app && uv run python scripts/traffic.py --mode demo` to produce the before/after telemetry.
5. Open <http://localhost:3000>, press **Investigate**. SSE stream + tool timeline + investigation card all populate.
6. When green: `cd .. && make deploy` (after creating `dynatrace-mcp-token` secret in Secret Manager).

`STUB_DYNATRACE_TOOLS=true` and `STUB_GEMINI=true` let everything run end-to-end without external credentials — useful for the first frontend pass.

## What's left

Code is complete for both submissions. Remaining work, in rough dependency order:

- **Arize**: Phoenix Cloud signup → `make seed && make run-loop` against real Phoenix. Confirm Phoenix MCP `upsert-prompt` works inside ADK from the Cloud Run image; if not, fall back to a Phoenix REST helper.
- **Dynatrace**: tenant + OTel wiring for `refund-assistant`; run `traffic.py --mode demo` and confirm change-analysis lights up in Dynatrace UI.
- **Prompt polish on live data**: the QA agent's instruction + the six judge prompts + the guard agent's system prompt all need iteration once you can see real Gemini output. This is the highest-leverage polish work left.
- **Cloud Run deploys** of both stacks + public Phoenix workspace snapshot for judging-window persistence.
- **Two demo videos** (≤3 min each on YouTube unlisted) + Devpost narrative for each.
- **Submit both** before the hard cutoff.
