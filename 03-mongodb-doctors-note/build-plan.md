# Build plan — MongoDB path (May 26 to June 11, 2026)

17 days from "pivot committed" to "submitted with buffer."

Deadline: **June 11, 2026, 2:00 PM PDT**  
Internal target submit: **June 9, 2026, 8:00 PM PDT**

## Resource map

This build plan is aligned to the official Devpost resource buckets so the final
submission clearly uses the stack the judges expect:

| Resource bucket | What we use |
|---|---|
| Core frameworks & environment | GCP trial / credits, Vertex AI, Agent Builder or Agent Runtime, Atlas free tier |
| Action mechanisms & data connectivity | Official MongoDB MCP server, Atlas Vector Search, seeded Atlas collections |
| Reasoning, state, & logic hosting | Python FastAPI service on Cloud Run, Atlas `user_vault`, Gemini extraction + synthesis |
| Deployment & safety | Secret Manager, Gemini safety settings, Cloud Run hosted URL |

We intentionally **do not** use Agent Builder Data Stores as the main knowledge
layer here, because Atlas needs to be visibly load-bearing for the MongoDB
track. If we need a lightweight public FAQ page later, Data Stores can be an
optional add-on, not the core.

## Phase 1 — Environment and core loop (May 26–28)

### Day 1 — Tue May 26

**Goal:** Lock the MongoDB path and remove rules risk.

- [ ] Freeze the active concept as "radiology report explanation," not "general medical copilot."
- [ ] Update all docs to remove non-Google AI dependencies.
- [ ] Create / confirm GCP project, billing, Vertex AI access, and Atlas cluster.
- [ ] Confirm the exact Google embedding model we will use and record its vector dimension.
- [ ] Create Secret Manager entries for `MONGODB_URI` and any runtime config we do not want in plaintext.

**Demoable artifact:** Repo docs and strategy now reflect one clear MongoDB path.

### Day 2 — Wed May 27

**Goal:** First real extraction call.

- [ ] Wire `extractor._gemini_extract` to Vertex AI.
- [ ] Test with one sample PDF and one pasted-text report.
- [ ] Normalize output into `ExtractedReport` so retrieval can depend on stable fields.
- [ ] Add one obvious failure-mode test: unreadable PDF returns a soft, safe fallback.

**Demoable artifact:** `POST /decode` extracts real fields from a sample report.

### Day 3 — Thu May 28

**Goal:** MongoDB MCP retrieval is live.

- [ ] Start the MongoDB MCP server in local dev and document the exact invocation.
- [ ] Wire `main.py` lifespan to launch / verify the MCP session.
- [ ] Wire `retriever.retrieve` to call MCP `aggregate`.
- [ ] Seed one narrow corpus: thyroid nodule literature + one guideline + sample patient-experience snippets.

**Demoable artifact:** A real query returns Atlas hits through the MCP layer.

## Phase 2 — Atlas retrieval and product shape (May 29–June 1)

### Day 4 — Fri May 29

**Goal:** Real explanation end-to-end.

- [ ] Wire `responder.respond` to Gemini structured output.
- [ ] Require the disclaimer block in the validated response.
- [ ] Make the response card always include sources.
- [ ] Store at least one saved decode in `user_vault`.

**Demoable artifact:** Upload report -> retrieve -> explain -> cite sources.

### Day 5 — Sat May 30

**Goal:** Make Atlas feel indispensable.

- [ ] Expand the corpus to 3-4 narrow report types.
- [ ] Add structured pre-filters (`condition`, `severity_tier`, `published_year`, `language`).
- [ ] Add recency-aware reranking so new guidelines beat stale papers.
- [ ] Save prior explanations in Atlas and use them to answer "has this changed since last time?"

**Demoable artifact:** A visible retrieval panel that shows why MongoDB matters.

### Day 6 — Sun May 31

**Goal:** Minimal user-facing UI.

- [ ] Build a minimal upload page with one hero result card.
- [ ] Show three states clearly: uploading, retrieving, final explanation.
- [ ] Add a small "sources used" panel.
- [ ] Make the disclaimer above the fold, not hidden in a footer.

**Demoable artifact:** Browser-based demo, not just curl.

### Day 7 — Mon June 1

**Goal:** Safety hardening.

- [ ] Add banned-phrase checks for diagnostic language in the final response.
- [ ] Configure Gemini safety settings explicitly.
- [ ] Add fallback behavior when retrieval returns weak evidence.
- [ ] Make the UI wording consistently say "explain" and never "diagnose."

**Demoable artifact:** Safe response path survives at least 5 repeated runs.

## Phase 3 — Polish the judge story (June 2–6)

### Day 8 — Tue June 2

**Goal:** Demo determinism.

- [ ] Lock one sample report and one golden output flow.
- [ ] Trim the corpus so the top hits are predictable.
- [ ] Log the exact Atlas aggregation pipeline used in the successful run.
- [ ] Save 3-5 clean traces for rehearsal.

**Demoable artifact:** Rehearsable golden path.

### Day 9 — Wed June 3

**Goal:** Make the MongoDB money shot visible.

- [ ] Add a retrieval panel that shows literature, guideline, and patient-experience hits separately.
- [ ] Surface one simplified aggregation snippet in the UI or demo overlay.
- [ ] Show user-history retrieval from `user_vault` if time allows.

**Demoable artifact:** Judges can literally see Atlas doing the work.

### Day 10 — Thu June 4

**Goal:** Hosted environment.

- [ ] Deploy the FastAPI service to Cloud Run.
- [ ] Move runtime secrets to Secret Manager.
- [ ] Smoke test the public URL end-to-end.
- [ ] Confirm logs do not leak report contents or secrets.

**Demoable artifact:** Public hosted URL for the demo.

### Day 11 — Fri June 5

**Goal:** Devpost narrative and video prep.

- [ ] Write the "Inspiration", "What it does", and "How we built it" sections while the design is fresh.
- [ ] Finalize the 2:55 script.
- [ ] Prepare one clean on-screen Atlas aggregation snippet and one simple architecture slide.
- [ ] Decide whether to mention saved history in the video or keep the story retrieval-only.

**Demoable artifact:** Devpost draft plus recording checklist.

### Day 12 — Sat June 6

**Goal:** First full recording.

- [ ] Record 3 takes of the full demo.
- [ ] Keep the disclaimer visible the whole time.
- [ ] Verify the video shows Gemini, Atlas, MCP, and the output card.
- [ ] Cut a rough version under 3:00.

**Demoable artifact:** Rough-cut video.

## Phase 4 — Final polish and submit (June 7–11)

### Day 13 — Sun June 7

**Goal:** Reliability and cleanup.

- [ ] Run the hosted demo 10 times.
- [ ] Fix the most likely failure path.
- [ ] Clean repo docs, remove dead TODOs that would confuse judges.
- [ ] Double-check that only Google AI is used.

**Demoable artifact:** Stable hosted build.

### Day 14 — Mon June 8

**Goal:** Final video and Devpost.

- [ ] Re-record any weak beats.
- [ ] Export captions.
- [ ] Finalize the Devpost narrative and screenshots.
- [ ] Sanity-check the public repo and hosted URL from an incognito browser.

**Demoable artifact:** Final video URL and near-final Devpost page.

### Day 15 — Tue June 9

**Goal:** Submit early.

- [ ] Final dry-run.
- [ ] Submit on Devpost by the internal deadline.
- [ ] Post the hosted URL and repo URL in one safe place for later judging-window checks.

**Demoable artifact:** Submission confirmation.

### Day 16 — Wed June 10

**Goal:** Buffer.

- [ ] Watch the public Devpost page for formatting issues.
- [ ] Fix any broken links, rendering issues, or uptime problems.

### Day 17 — Thu June 11

**Goal:** Hands off except emergency fixes.

- [ ] Keep the hosted demo alive.
- [ ] Do not add scope.
- [ ] Let the deadline pass with a stable build.

## Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Safety framing drifts into diagnosis language | High | Narrow to report explanation only, add banned-phrase checks, keep disclaimer always visible |
| Atlas vectors and embedding dimensions drift | High | Centralize model + dimension config and assert alignment during seed/startup |
| MongoDB MCP version drift | Medium | Pin the MCP version for the demo container and smoke test before recording |
| Demo becomes too academic | Medium | Keep the UI simple and put the emotional before/after first |
| Retrieval is technically correct but hard to see | Medium | Show the retrieval panel and a simplified pipeline snippet in the video |
