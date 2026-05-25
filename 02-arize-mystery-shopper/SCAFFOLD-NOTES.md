# SCAFFOLD-NOTES — Voice-AI Mystery Shopper (Arize backup track)

Created May 23, 2026. This is the backup hackathon track scaffold. Primary submission is on the Fivetran track in `../01-fivetran-dtc-diagnostic/`. Depth target was roughly 60% of the primary; we landed close to that.

## What's complete

- **Pitch and positioning docs.** `README.md`, `architecture.md`, `demo-script.md` are submission-ready first drafts. Demo script is timed to 2:55 with a buffer; the cold open and payoff beats are locked, the architecture document explains the load-bearing role of Phoenix at three different layers (datasets, experiments, prompts).
- **Python package skeleton.** `agent/pyproject.toml` lists every dependency we will need with conservative lower-bound pins and `TODO: confirm` markers on the four packages whose 2026 versioning is uncertain (`google-cloud-aiplatform`, `arize-phoenix`, `arize-phoenix-evals`, `mcp`).
- **Configuration surface.** `agent/.env.example` documents twelve environment variables grouped by concern (Vertex AI, Phoenix, MCP, audit runtime, app).
- **HTTP surface.** `agent/main.py` has the three endpoints the demo needs (`POST /audit`, `GET /audit/{id}`, `GET /audit/{id}/report`), a Pydantic-validated request body, and a background-task executor wired into the lifespan handler.
- **Scenario library.** `agent/scenarios.py` ships exactly the ten scenarios specified, each with a real persona, opening message, anchor phrases, stop conditions, and primary dimensions. The dataclass schema is ready to round-trip through `add-dataset-examples` in Phoenix.
- **Judge prompts.** `agent/prompts.py` defines six versioned judge prompts (empathy, accuracy, escalation, bias, hallucination, brand voice). Each has an explicit 0 / 0.5 / 1.0 rubric and at least one explicit failure-mode warning (e.g., "do NOT reward sycophancy" in empathy, "saying I don't know is not a hallucination" in hallucination). Prompts are designed to be upserted into Phoenix unchanged.
- **Judge runner shape.** `agent/judge.py` runs all six judges per scenario, returns a structured `JudgeReport`, and exposes the four integration points where real Phoenix / Vertex AI calls slot in. Stubs are deterministic so the FastAPI app is end-to-end exercisable today without any external credentials.

## What's stubbed

These are the explicit "TODO" sites the real build will fill in. Each is small and well-scoped, which is the whole point of having the scaffold:

1. **Phoenix OTel tracer registration** at app startup (`main.py` lifespan handler). One function call once we confirm the `arize-phoenix` import path.
2. **Conversation orchestration** in `_run_audit`. Today it just calls the judge with no transcript; the real version drives Gemini 3 as the customer, calls a target adapter, loops until `stop_when` triggers.
3. **Target adapter layer.** No adapter implementations yet. MVP needs only the HTTPS-chat adapter; WebSocket and voice are post-MVP.
4. **Phoenix MCP client** for `get-latest-prompt` and `add-experiment-row`. The shape is sketched in `judge.py` comments; the actual `mcp.ClientSession` boot is one function we will share between `main.py` and `judge.py`.
5. **Phoenix dataset seeding.** A `scripts/seed_dataset.py` that takes `DEFAULT_SCENARIO_SET` and posts it to Phoenix via `add-dataset-examples`. One-time job.
6. **Report renderer.** The data structure (`JudgeReport`) is fixed; an HTML template plus a per-target leaderboard view is needed before the demo.
7. **Dockerfile + Cloud Run deploy.** README documents the intent but neither file ships yet.
8. **Frontend.** No frontend in this scaffold at all. The demo can run against the JSON API plus a hand-built static HTML report for the recording, or we can add a thin React page in a day if there's time.

## Estimated remaining work to demo-able state

Person-hours, assuming Gemini 3 access is unblocked and a working Phoenix Cloud account is in hand. "Demo-able" means the recorded demo in `demo-script.md` runs end-to-end against four real third-party AIs, not just mocks.

| Workstream | Hours |
|---|---|
| Phoenix tracer wiring + smoke test trace round-trip | 2 |
| MCP client bootstrap + dataset/experiment/prompt helpers | 4 |
| Seed dataset script (push 50 scenarios into Phoenix) | 2 |
| Generate scenarios 11-50 (curate, write, review) | 6 |
| Gemini 3 customer-role orchestrator with `stop_when` loop | 6 |
| HTTPS chat target adapter + 4 target-specific config files | 4 |
| Real judge calls replacing the stubs in `judge.py` | 3 |
| Report renderer (HTML + leaderboard logic) | 6 |
| Dockerfile, Cloud Run deploy, secret manager wiring | 3 |
| Pre-recorded "live" audit run + caching layer for the demo | 4 |
| Demo polish, narration, video edit | 6 |
| Buffer for one full day of unknowns | 8 |
| **Total** | **~54 hours** |

For comparison the primary Fivetran scaffold is sized at roughly 90 person-hours from its scaffold state. The lighter scope here is intentional and tracks the original spec.

## Top three risks

1. **Phoenix MCP-vs-SDK boundary turns out wrong.** The scaffold uses MCP for control-plane operations (datasets, experiments, prompts) and the Python SDK directly for OTel tracing. If the 2026 MCP package can't actually drive `add-experiment-row` end-to-end, we have to fall back to the SDK for experiments and the demo's "everything is in Phoenix" narrative weakens. Mitigation: spike the MCP path on day 1 of any pivot, before scenario authoring. Time at risk: ~6 hours of judge-runner work.
2. **Rate-limited or blocked by target AIs.** Real hotel-chain chatbots may block automated traffic, return generic fallbacks, or simply hit rate limits halfway through the 50-scenario run. The demo specifically promises a head-to-head between Marriott / Hilton / Hyatt / IHG; if even one of them blocks us, the leaderboard story collapses. Mitigation: use targets we can guarantee access to (open-source bots, our own deployed reference bot, public demo endpoints from each vendor) and frame the four hotel chains as a synthetic stand-in if needed. The scoring methodology is the product; the specific targets are dressing.
3. **Judge variance is too high to give clean rankings.** LLM-as-judge can be noisy enough that a leaderboard reorders between runs, which destroys the demo's credibility. Mitigation: run each judge call N=3 times and report median+IQR; pre-compute variance per dimension across all 200 conversations in the cached demo run and surface it in the report so reviewers see we measured it. This adds 3x judge cost but the audit budget can absorb it.

## Decision gates

Per `../DECISION.md`, we evaluate pivoting on Day 4 (May 27). Two scenarios trigger this scaffold becoming the actual submission:

- Fivetran free trial proves too restrictive to demo six connectors realistically.
- Gemini Enterprise Agent Builder access is blocked through Day 3 and Vertex AI direct usage isn't enough for the Fivetran demo's full loop.

If we pivot, day 1 of the pivot opens by running the spike in risk #1 above before any other work.
