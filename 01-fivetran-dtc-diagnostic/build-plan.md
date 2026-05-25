# Build plan — May 24 to June 11, 2026

19 days from "scaffold complete" to "submitted ≥48 hours before deadline."
Deadline: **June 11, 2026, 2:00 PM PDT**. Internal target submit: **June 9, 8:00 PM PDT**.

Three phases:

| Phase | Days | Goal |
|---|---|---|
| Phase 1 — Prove the loop | May 24–30 (7 days) | End-to-end agent runs against fake data, returns a real-looking report |
| Phase 2 — Real integrations | May 31–June 5 (6 days) | Real Fivetran MCP, real BigQuery, real Gemini, real dashboard |
| Phase 3 — Polish + submit | June 6–11 (6 days) | Demo video, Devpost writeup, hardening, submit |

Each day has: **Goal** (one sentence), **Tasks** (concrete), **Demoable artifact**
(what is visible at end of day), and **Blocking risks**.

Blocking dependencies on partner approvals are flagged with `[BLOCKER:partner]`.

---

## Phase 1 — Prove the loop (May 24–30)

### Day 1 — Sun May 24

**Goal:** Get all the gating accounts and credits in motion.

- [ ] `[BLOCKER:gcp-credit]` Submit GCP $100 credit form (1–5 day approval).
- [ ] Activate GCP free trial ($300, 90 days). Use it as bridge while waiting.
- [ ] Create GCP project: `rapid-agent-hack-2026`.
- [ ] Enable APIs: Vertex AI, Cloud Run Admin, Cloud Functions, Secret Manager,
      Cloud Build, BigQuery.
- [ ] `[BLOCKER:agent-builder]` Request Agent Builder access if not on by default.
- [ ] Verify Gemini 3 model access in Vertex AI Model Garden.
- [ ] `[BLOCKER:fivetran]` Sign up for Fivetran 14-day trial. **Do not start the
      trial clock yet** — make the account but do not confirm any sources until
      Day 8 (when we actually need them).
- [ ] MongoDB Atlas free M0 cluster, get connection string.
- [ ] Sign up for Shopify Partner / Klaviyo / Stripe test / Meta sandbox /
      Google Ads test / TikTok for Business / Yotpo trial.

**Demoable artifact:** Project README + this build plan committed to GitHub repo.

**Risks:** GCP credit approval is 1–5 business days. If credit is not approved by
Day 4, the $300 free trial covers us — no real risk.

### Day 2 — Mon May 25

**Goal:** First Gemini 3 call from Python on Cloud Run.

- [ ] Set up local Python 3.11 venv per `agent/README.md`.
- [ ] Install dependencies. Verify all pinned versions resolve.
- [ ] Wire `agent/src/agent/config.py` to read from `.env`.
- [ ] Replace the Gemini stub in `agent_loop.py` with a real Vertex AI call.
- [ ] Run a "hello world" agent call locally: ask Gemini one question with
      one tool, see a tool call come back.
- [ ] Build the agent service Docker image (`infra/Dockerfile`).
- [ ] Deploy to Cloud Run as `dtc-agent-dev`. Hit `/healthz` from the public URL.

**Demoable artifact:** `curl https://dtc-agent-dev-xxx.run.app/healthz` → 200 OK.
First end-to-end Gemini round-trip works.

**Risks:** Vertex AI quota — Gemini 3 may be metered. Bookmark the quota page.

### Day 3 — Tue May 26

**Goal:** Get the Fivetran MCP server running and reachable from the agent.

- [ ] Clone https://github.com/fivetran/fivetran-mcp.
- [ ] Run it locally with `FIVETRAN_API_KEY` + `FIVETRAN_API_SECRET` +
      `FIVETRAN_ALLOW_WRITES=true`.
- [ ] Manually invoke `list_connections` to confirm auth.
- [ ] Decide deployment shape: same-Cloud-Run-service sidecar vs. separate
      Cloud Run service. Default: separate service `fivetran-mcp-dev`.
- [ ] Deploy MCP to Cloud Run. Lock its invoker IAM to the agent service's
      service account.
- [ ] Implement `agent/src/agent/tools.py` HTTP client. Replace stubs with real
      HTTP calls to the MCP. Confirm `setup_connector(source="shopify")` works.
- [ ] **Decision-gate (Day 4 in plan, but check today):** does Fivetran trial
      let us create 7 connections at once? If no, scope down to 4 connectors
      for the demo and document the rationale.

**Demoable artifact:** `python -m agent.cli setup_connector shopify` actually
creates a Fivetran connection (visible in the Fivetran dashboard).

**Risks:** Fivetran trial may rate-limit connector creation; may not include
all 7 sources we want. Mitigation: pre-validate on Day 1.

### Day 4 — Wed May 27 — **DECISION GATE**

**Goal:** Confirm we are sticking with Fivetran or pivot to backup.

Use the criteria in `../DECISION.md`:
- [ ] Is GCP Agent Builder accessible? (If no → pivot to Vertex AI direct.)
- [ ] Is Fivetran trial workable for the demo? (If no → pivot to Arize backup.)
- [ ] Did we get 4+ partner sandboxes working? (If no → pivot to MongoDB backup.)

If any of these are red, pivot today. We have 14 days left, which is enough for
the Arize or MongoDB backup if we move now.

If green:
- [ ] Connect BigQuery as Fivetran's destination. Pick `fivetran_velvetmint`
      dataset.
- [ ] Manually trigger a Shopify sync. Verify rows land in BigQuery.

**Demoable artifact:** A decision note appended to `DECISION.md`. BigQuery rows
visible if green.

### Day 5 — Thu May 28

**Goal:** Finish the agent loop end-to-end with stubbed analytics.

- [ ] Wire `agent_loop.py` ReAct loop to fully iterate: model → tool → model.
- [ ] Implement SSE streaming in `main.py` (`StreamingResponse`,
      `text/event-stream`).
- [ ] Implement MongoDB persistence: write user message, agent reasoning,
      tool calls, tool results, final report.
- [ ] Stub `diagnostic_engine.run_battery()` to return three hard-coded findings
      that match the demo script.
- [ ] Verify a full `POST /diagnose` call produces a report end-to-end.

**Demoable artifact:** `curl -N -X POST .../diagnose` streams reasoning lines
and ends with a final JSON report. Full loop works (with stubbed analytics).

**Risks:** SSE through Cloud Run can be tricky — confirm `keepalive`,
`response_mode="text/event-stream"`, and 60-second cold-start tolerance.

### Day 6 — Fri May 29

**Goal:** Seed VelvetMint data into BigQuery (the demo dataset).

- [ ] Write `scripts/seed_velvetmint.py` that generates 90 days of synthetic
      data for: Shopify orders, Klaviyo events, Meta/Google/TikTok ad
      insights, Stripe charges, Yotpo reviews.
- [ ] Plant the 3 anomalies: TikTok creative fatigue starting May 2, Klaviyo
      popup broken May 3, iOS Safari checkout JS error May 8.
- [ ] Load into BigQuery `fivetran_velvetmint.*` tables. Match the schemas
      Fivetran would actually produce so the diagnostic queries are realistic.

**Demoable artifact:** BigQuery dataset exists with realistic seeded data.

**Risks:** Schema-matching to Fivetran's real output is tedious. Use Fivetran's
schema docs as ground truth.

### Day 7 — Sat May 30

**Goal:** Real diagnostic engine returning real findings on real (seeded) data.

- [ ] Implement the 12 diagnostic queries in `diagnostic_engine.py`.
      Start with the 3 that match the demo. Add others if time allows.
- [ ] Each query returns a `Finding` with `metric`, `current`, `baseline`,
      `delta_pct`, `dollar_impact`, `recommended_fix`.
- [ ] Wire the agent's `query_synced_data` tool to hit the BigQuery client.
- [ ] Run `POST /diagnose` end-to-end with `question="why is revenue down?"`.
      Confirm the agent's final report contains the 3 expected findings.

**Demoable artifact:** A full diagnosis runs from question → tool calls → real
BigQuery analysis → 3 findings. Phase 1 done.

---

## Phase 2 — Real integrations + dashboard (May 31–June 5)

### Day 8 — Sun May 31

**Goal:** Frontend skeleton.

- [ ] Scaffold the Next.js 15 project in `frontend/`. App router, TypeScript,
      shadcn/ui, Tailwind.
- [ ] Set up the three pages: `/`, `/dashboard`, `/diagnoses/[id]`.
- [ ] Build the chat input + reasoning panel + diagnosis card components.
      Skeleton only, no real wiring.
- [ ] Deploy to Cloud Run as `dtc-frontend-dev`.

**Demoable artifact:** Public URL renders the dashboard with a fake conversation.

### Day 9 — Mon June 1

**Goal:** Connect the dashboard to the agent service over SSE.

- [ ] Implement `EventSource` client in the dashboard.
- [ ] Render reasoning events as they stream in.
- [ ] Render tool-call/tool-result events as expandable items.
- [ ] Render the final structured report card.
- [ ] Confirm a real diagnosis flows from browser → agent → MCP → BigQuery →
      report → browser.

**Demoable artifact:** Open browser, type the question, watch the reasoning
stream live. End-to-end demo works (without polish).

### Day 10 — Tue June 2

**Goal:** Replace any remaining stubs with the real thing. Polish prompt.

- [ ] Promote `agent/src/agent/prompts.py` system prompt with at least 3
      few-shot examples from real diagnoses.
- [ ] Tune Gemini 3 hyperparameters: temperature, max output tokens, JSON mode
      where appropriate.
- [ ] Add the connector-status polling logic with a sane retry/backoff.
- [ ] Replace the synthetic Klaviyo / Meta / TikTok data with real Fivetran
      sync output if any of those connectors actually worked end-to-end during
      the trial. Keep the synthetic seed as a fallback.

**Demoable artifact:** A run that uses real Fivetran-synced data for at least
2 sources. Diagnosis still names the same 3 findings (deterministic).

### Day 11 — Wed June 3

**Goal:** Cloud Function webhook + auth hardening.

- [ ] Implement `/start-diagnosis` Cloud Function.
- [ ] Wire the dashboard's "start diagnosis" button to hit the Cloud Function
      (instead of going direct to the agent).
- [ ] Lock down IAM: only the function can invoke the agent's `/diagnose`.
- [ ] Move all secrets to Secret Manager. Confirm Cloud Run reads them.

**Demoable artifact:** End-to-end run via Cloud Function URL. Secrets are
managed.

### Day 12 — Thu June 4

**Goal:** Reliability run and prompt tuning.

- [ ] Run the full diagnosis 20 times back-to-back. Track pass rate.
- [ ] Fix the failure modes — bad tool-call JSON, MCP timeout, BigQuery query
      error, Gemini hallucinating an unknown source.
- [ ] Tighten the system prompt to make tool calls more reliable. Add explicit
      tool-call schema and "if you don't know, say so" guard rails.
- [ ] Target: 18+/20 successful runs.

**Demoable artifact:** A pass-rate log. Stable demo.

### Day 13 — Fri June 5

**Goal:** Visual polish.

- [ ] Brand the frontend: VelvetMint demo logo, color palette,
      typography pass.
- [ ] Animate the reasoning panel (typewriter effect, line by line).
- [ ] Build the connector-creation visual: animated "creating Shopify…"
      cards with progress dots.
- [ ] Build the finding chart for each diagnosis card (a small line chart
      showing the metric drop on the date of the anomaly).
- [ ] Empty / loading / error states for the dashboard.

**Demoable artifact:** A pretty, polished dashboard. Phase 2 done.

---

## Phase 3 — Polish + submit (June 6–11)

### Day 14 — Sat June 6

**Goal:** Record the demo video, take 1.

- [ ] Run the full demo end-to-end 3 times to find timing issues.
- [ ] Record narration audio first (cleaner workflow).
- [ ] Screen-record three takes of the demo with narration.
- [ ] First rough cut at 3:00 length.

**Demoable artifact:** Rough-cut video file in `demo/` (gitignored or in
Drive).

### Day 15 — Sun June 7

**Goal:** Recut, retake, finalize the video.

- [ ] Watch with fresh eyes. Note pacing problems.
- [ ] Recut to 2:55 to leave a buffer.
- [ ] Burn-in captions for accessibility.
- [ ] Upload to YouTube as **unlisted**, capture the URL.

**Demoable artifact:** Final video URL.

### Day 16 — Mon June 8

**Goal:** Devpost writeup + repo polish.

- [ ] Write the Devpost project page: "Inspiration", "What it does",
      "How we built it", "Challenges", "Accomplishments", "What we learned",
      "What's next".
- [ ] Add Apache-2.0 LICENSE at the workspace root.
- [ ] Final pass on README.md, architecture.md, agent/README.md.
- [ ] Add a `CONTRIBUTING.md` and a couple of GitHub issue templates (signals
      "real open-source project" to judges).
- [ ] Make sure no secrets, env files, or PII are in the commit history
      (`gitleaks scan` clean).

**Demoable artifact:** Devpost draft saved. Repo polished.

### Day 17 — Tue June 9

**Goal:** Submit. Buffer day for Wednesday.

- [ ] Final 5 dry-runs of the live demo to confirm the deployed services are
      stable.
- [ ] Hit submit on Devpost. Internal target: 8:00 PM PDT, ≥48 hours before
      the June 11 2:00 PM PDT deadline.
- [ ] Tweet / post to Discord that the project is up.

**Demoable artifact:** Submission confirmation email.

### Day 18 — Wed June 10

**Goal:** Buffer. Re-record or re-submit if anything broke.

- [ ] Watch the public Devpost render of the project page.
- [ ] If anything is off, fix it. Devpost allows edits up to the deadline.
- [ ] If the deployed services failed overnight, fix.

**Demoable artifact:** Stable submission.

### Day 19 — Thu June 11

**Goal:** Hands off the keyboard.

- [ ] Watch the deadline pass at 2:00 PM PDT.
- [ ] Post to the hackathon Discord with a link to the project.
- [ ] Sleep.

---

## Risks summary

| Risk | Impact | Mitigation |
|---|---|---|
| Agent Builder access not granted | High | Day-1 request; backup is Vertex AI direct |
| Fivetran trial is restrictive | High | Day-1 evaluate; backup is Arize track |
| Gemini 3 quota limits | Medium | Watch quotas; request increase Day 1 |
| Live MCP-driven connector creation is too slow for the demo | Medium | Pre-record beats 3–5; keep beats 6–10 live |
| Dashboard SSE through Cloud Run is flaky | Medium | Day-5 spike; fall back to polling if needed |
| iOS Safari checkout-JS finding is too "specific" — judges think it's planted | Low | Show the BigQuery query in the report card so it is reproducible |
| Solo dev burns out before June 11 | High | Strict day-by-day; use buffer days; submit Day 17 not Day 19 |

## Daily standup format

End of each day, write to `STATUS.md`:

- What I shipped today
- What I am stuck on
- What I'll do tomorrow
- Risks added or removed
