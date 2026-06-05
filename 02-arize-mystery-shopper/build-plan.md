# Build Plan — 16 days to ship

Today is **Tue May 26**. Submission deadline is **Thu Jun 11, 2:00 PM PDT**. Target submission **Tue Jun 9** (≥48 hours of buffer per `00-shared/hackathon-rules.md`). Effective build window: **15 days**.

Self-scoring rubric reminder (from `00-shared/judging-rubric.md`): we must hit 9+/10 on all four criteria by Day 14. Tiebreaker order is Tech → Design → Impact → Idea so we front-load engineering depth.

## Big-picture phases

| Phase | Days | Outcome |
|---|---|---|
| **0 — Pivot** | done (May 26) | DECISION updated, scaffold ADK-ified, SUT seeded with three flaws |
| **1 — Smoke** | May 27 — May 28 | One full trace cycle visible in Phoenix Cloud. Phoenix MCP toolset returns real data. |
| **2 — Real run** | May 29 — Jun 1 | Real `run_scenario` against the SUT. Real Gemini judge replaces stubs. Baseline experiment writes to Phoenix. |
| **3 — Self-improve** | Jun 2 — Jun 4 | Cluster + mutate + `upsert-prompt` + re-run produces measurable score delta. |
| **4 — UX + deploy** | Jun 5 — Jun 7 | Next.js dashboard with live thinking panel + embedded Phoenix iframe. Cloud Run deploy. |
| **5 — Polish + record** | Jun 8 — Jun 9 | Pre-record demo, write Devpost narrative, submit. |
| **6 — Buffer** | Jun 10 — Jun 11 | Reserved. Touch nothing unless required. |

## Day-by-day

### Day 1 — Tue May 26 (today) — DONE
- [x] Re-read Arize partner page. Identify the self-improvement criterion.
- [x] Update `DECISION.md` and root `README.md` to promote Arize to primary.
- [x] Rewrite concept docs (`README.md`, `architecture.md`, `demo-script.md`).
- [x] Switch agent scaffold to ADK + OpenInference + Phoenix MCP `McpToolset`.
- [x] Add the deliberately-flawed VelvetMint SUT.
- [x] Wire the three QA tools as stubs (`run_scenario`, `cluster_failures`, `mutate_sut_prompt`).
- [x] Update `pyproject.toml`, `.env.example`, `Makefile`, `README.md`.

### Day 2 — Wed May 27 — Phoenix smoke + dataset seed
- [ ] Create Phoenix Cloud account → grab `PHOENIX_API_KEY` (`px_live_...`) and **full** hostname URL (with `/s/<space>`).
- [ ] Set both in `.env`; `make smoke` succeeds with `phoenix tracer: ok`.
- [ ] Confirm Vertex AI is enabled in `GOOGLE_CLOUD_PROJECT`; `gcloud auth application-default login` done.
- [ ] `make run-sut MESSAGE="..."` — first traced SUT turn appears in Phoenix.
- [ ] `make seed` — wire the seed script to the real Phoenix Python client. After this completes, Phoenix has:
  - dataset `velvetmint-support.scenarios` with 10 examples
  - 6 judge prompts (`judge.empathy.v1` etc.)
  - SUT seed prompt `sut-velvetmint-support` v1
- [ ] Attend the [Phoenix MCP Discord build session at 1pm EDT](https://discord.com/events/861966823054639134/1505960468118900736). Ask Richard Young (ryoung@arize.com) about the canonical pattern for upserting experiment rows via MCP vs. SDK.

### Day 3 — Thu May 28 — Phoenix MCP via ADK toolset
- [ ] First call from inside the QA agent to a Phoenix MCP tool. Smallest possible: `list-datasets`.
- [ ] Verify the call appears as a child span under the QA agent's reasoning trace.
- [ ] Wire `get-latest-prompt` resolution so `run_scenario` actually loads the SUT prompt by version rather than reading the seed file.
- [ ] Decide MCP-vs-SDK boundary definitively (see Risk #1 below). Lock it in `architecture.md`.

### Day 4 — Fri May 29 — Real `run_scenario`
- [ ] Replace `_stub_drive_conversation` in `qa_agent/tools/scenarios.py` with the ADK driver. The driver:
  - A small Gemini 2.5 Flash agent playing the customer.
  - Uses `scenario.persona`, `scenario.opening_message`, and respects `must_say`, `stop_when`, `AUDIT_MAX_TURNS`.
- [ ] Verify one full scenario produces a clean Phoenix session with N>=4 SUT turns.
- [ ] Run all 10 scenarios against the baseline SUT. Confirm the three flawed scenarios fail in visible ways in the trace.

### Day 5 — Sat May 30 — Real judges (Gemini-only)
- [ ] Replace `_stub_judge` with real Gemini calls. Resolve each judge prompt via Phoenix MCP `get-latest-prompt`. Run `AUDIT_JUDGE_REPLICAS=3` for variance.
- [ ] Per-(scenario, dimension, replica) row written to a Phoenix experiment via MCP (or SDK — TBD on Day 3).
- [ ] Baseline experiment in Phoenix shows ~60-70% pass rate with the three planted failures clearly red.
- [ ] **Self-score check (target: Tech 6, Design 4, Impact 8, Idea 9 = 27/40).** Adjust if behind.

### Day 6 — Sun May 31 — Scenario set to 50
- [ ] Curate 40 additional scenarios across the six dimensions; mix paired-bias probes and ambiguous-intent. Push via `add-dataset-examples`.
- [ ] Confirm baseline run on 50 scenarios stays under 12 minutes of wall-clock (parallelism via `AUDIT_MAX_CONCURRENCY=4`).
- [ ] Snapshot cost. If a baseline run is > $0.50 we shave replica count or turn cap.

### Day 7 — Mon Jun 1 — Cluster + mutate
- [ ] Replace `_stub_cluster` with real Gemini 2.5 Flash clustering. Validate output schema with a strict JSON parser; reject + retry on malformed.
- [ ] Replace `_stub_mutate` with real Gemini 2.5 Pro mutation. Verify it only appends.
- [ ] Print the diff in CLI mode.

### Day 8 — Tue Jun 2 — End-to-end loop
- [ ] `make run-loop` runs: baseline → introspect → cluster → mutate → `upsert-prompt` → post-fix run → delta report.
- [ ] Verify Phoenix now has prompt v1 + v2 + two experiments linked by parent_prompt_hash.
- [ ] Delta on the targeted dimension is positive and statistically distinguishable (p < 0.05 over the affected scenarios).

### Day 9 — Wed Jun 3 — Frontend scaffold
- [ ] `frontend/` Next.js app: pages = home + audit detail.
- [ ] SSE consumer for `/audit/{id}/events`. Render the thinking panel.
- [ ] Embed Phoenix UI as an iframe in a side panel (Phoenix supports embedded mode).

### Day 10 — Thu Jun 4 — Frontend polish
- [ ] Final report table (per-dimension, baseline vs post-fix, deltas, p-values).
- [ ] Evidence panel: click a failing scenario → side-by-side v1 vs v2 transcript with judge rationales.
- [ ] **Self-score check (target: Tech 8, Design 7, Impact 8, Idea 9 = 32/40).**

### Day 11 — Fri Jun 5 — Cloud Run deploy
- [ ] Dockerfile (Python 3.12 slim + Node 18+ for npx).
- [ ] `make deploy` ships QA backend.
- [ ] Frontend separately deployed (Cloud Run or Vercel — Vercel is fine, it doesn't compete with GCP for compute).
- [ ] Secrets bound from Secret Manager per `00-shared/SECRET-MAP.md`.
- [ ] Public hosted URL works in an incognito window with no login.

### Day 12 — Sat Jun 6 — End-to-end on the deployed instance
- [ ] Run the loop against the hosted URL. Should match local behavior.
- [ ] Snapshot the Phoenix workspace so the judging-window URL has data on it.
- [ ] **Self-score check (target: 9/8/8/9 = 34/40).** Reduce scope if below 8 anywhere.

### Day 13 — Sun Jun 7 — Demo recording
- [ ] Record the 3-minute demo per `demo-script.md`. Two takes, pick the better one.
- [ ] Verify ≤ 3:00 total. Cut to 2:55 if needed.
- [ ] Upload to YouTube (NOT Loom — Loom is disqualifying). Make unlisted.

### Day 14 — Mon Jun 8 — Devpost writeup + safety section
- [ ] Devpost text description: features, tech stack, what it does, how Phoenix is used, learnings.
- [ ] Add Responsible-AI section to the README (per `00-shared/google-cloud-stack.md`).
- [ ] Apache-2.0 LICENSE file at root verified.
- [ ] Repo is public.

### Day 15 — Tue Jun 9 — Final sweep + submit
- [ ] **Self-score: target 9+/9+/9/9+ = 36+/40.**
- [ ] One full incognito-window pass through hosted URL + repo + video + Devpost form.
- [ ] **Submit by 5pm PT** (well before the 2pm PT Jun 11 deadline).

### Days 16-17 — Wed Jun 10 / Thu Jun 11 — Buffer
- [ ] Reserved for emergencies. Do not touch the submission.
- [ ] If everything is green, OPTIONALLY ship the Fivetran scaffold as a second submission (rules allow it, see `DECISION.md` stretch section).

## Stretch — second submission

Only if Day 13 ends with submission-ready Arize work AND Fivetran trial is still active locally:

- Day 14 morning: ship a minimal Fivetran DTC Diagnostic with the existing scaffold.
- Day 14 afternoon: record its demo (recorded against LIVE Fivetran trial).
- Day 15: submit both.
- Per rules Section 7: a single submission wins one prize; two submissions to two tracks = two shots.

## Top risks and mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Phoenix MCP `upsert-prompt` via npx subprocess in Cloud Run** doesn't work as expected (sandbox / spawn issues). | Medium | High | Day 3 spike. Fallback: call Phoenix REST API directly from a Python helper tool while keeping MCP for the read-mode tools. We still hit "meaningful use of MCP" criterion via list-traces / get-spans / etc. |
| 2 | **Judge variance reorders the leaderboard** between baseline and post-fix runs, killing the demo's punch. | Medium | High | N=3 replicas. Report median + IQR. Targeted prompt fix on a high-variance-free dimension (hallucination is the most stable in our internal tests). |
| 3 | **Gemini 2.5 Pro refuses to mutate the SUT prompt minimally** (rewrites the whole thing or is too cautious). | Low-Medium | High | Tight system instruction (already in `qa_agent/prompt.py`). JSON-schema-strict output. Validate diff is additive in `mutate_sut_prompt` before returning. |
| 4 | **`openinference-instrumentation-google-adk` version drift** vs. our `google-adk` pin. | Low | Medium | Match the Arize reference repo's lower bounds. Smoke test on Day 2 is the canary. |
| 5 | **Phoenix Cloud endpoint URL format gotcha** (the `/s/<space>` thing). | High before fix, near-zero after | Medium | Already handled: `instrumentation.py` warns loudly if the env var looks wrong. |
| 6 | **Cost overrun** if a single run is > $1. | Low | Low | Day 6 snapshot. SUT is on Flash. We can cut replicas from 3 to 1 in a pinch. |

## What changes the plan

We re-evaluate the plan at the end of Day 5 (Sat May 30). If we are behind on the Tech self-score (< 6), we either drop the multi-cycle stretch and lock in single-cycle for the demo (lower tech score but still A− on the criterion) or pivot to the Fivetran backup (re-read `DECISION.md` to see what survives).
