# SCAFFOLD-NOTES — Self-Improving QA Agent (Arize primary track)

Updated **May 26, 2026** (post-pivot). The prior "Voice-AI Mystery Shopper" scaffold was retargeted to "Self-Improving QA Agent" after re-reading the Arize partner page; the partner explicitly named the self-improvement loop as a bonus-criterion. See `../DECISION.md` for the full pivot rationale.

## What's complete

- **Strategy.** `../DECISION.md` and `../README.md` updated. Arize promoted to primary; Fivetran kept as backup + stretch second submission.
- **Concept docs.** `README.md`, `architecture.md`, `demo-script.md`, `build-plan.md` are first-draft submission-ready. Demo script is timed to 2:55 with a buffer; the architecture document explains the load-bearing role of Phoenix at five layers (datasets, experiments, prompts, traces/sessions, annotations).
- **Stack alignment with the canonical Arize reference.** `pyproject.toml`, `.env.example`, and `Makefile` mirror the [Arize gemini-hackathon repo](https://github.com/Arize-ai/gemini-hackathon) (Google ADK + `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)` + `arize-phoenix>=7.0` + Apache-2.0).
- **Phoenix tracer** wired in `qa_agent/instrumentation.py`. Includes a defensive warning for the Phoenix Cloud endpoint format gotcha (must include `/s/<space>`).
- **ADK QA agent** with three FunctionTools and a Phoenix MCP `McpToolset`. `qa_agent/agent.py` is the load-bearing piece — it's what makes "agent introspects its own traces at runtime via MCP" literally true.
- **QA agent system instruction** in `qa_agent/prompt.py` — six-phase, opinionated, written to drive the demo's payoff. This is the most consequential prompt in the repo.
- **Subject Under Test (SUT)** in `sut/agent.py` + `sut/prompt.py` + `sut/tools.py`. Three deliberate pathologies (hallucinated 90-day price-match, dropped Spanish code-switching, fraud-resolved-in-channel) flagged with `# FLAW` markers.
- **Three QA tools** (`run_scenario`, `cluster_failures`, `mutate_sut_prompt`) with the right shapes, deterministic stubs so the loop is exercisable end-to-end, and explicit TODO markers at each real-call site.
- **CLI + FastAPI surface** in `qa_agent/main.py`. Matches the pattern from the canonical reference repo's `agent/main.py`.
- **Seed script** in `scripts/seed_phoenix.py` (manifest level — wire-up TODO is Day 2).
- **Six judge prompts** preserved from the prior Mystery Shopper scaffold in `judge_prompts.py` (renamed from `prompts.py`). Each has explicit 0/0.5/1.0 rubric + at least one failure-mode warning.
- **Ten seed scenarios** preserved in `scenarios.py`. Three of them now directly map to the SUT's planted flaws (`hallucination-bait-policy`, `accent-spanish-en`, `escalation-fraud`).

## What's stubbed (the TODO sites)

These are deliberate. The scaffold lets the QA agent's full six-phase loop run end-to-end against deterministic stubs so the integration shape is locked in before we burn Gemini calls.

| # | Site | What it does today | What it does in the real build |
|---|---|---|---|
| 1 | `qa_agent/tools/scenarios.py` TODO(1) | reads SUT prompt from `sut/prompt.py` directly | resolves SUT prompt from Phoenix by version id via `get-prompt-version` |
| 2 | `qa_agent/tools/scenarios.py` TODO(2) | `_stub_drive_conversation` returns a fixed 2-turn transcript | boots ADK runner for SUT, drives with Gemini 2.5 Flash playing the customer, traces every turn |
| 3 | `qa_agent/tools/scenarios.py` TODO(3) | `_stub_judge` returns deterministic scores keyed off `primary_dimensions` | calls Gemini 2.5 with each of the six judge prompts (resolved via `get-latest-prompt`), N=3 replicas |
| 4 | `qa_agent/tools/cluster.py` TODO | `_stub_cluster` groups by dimension | one Gemini 2.5 Flash call with the strict cluster prompt |
| 5 | `qa_agent/tools/mutate.py` TODO | `_stub_mutate` appends a hardcoded sentence | one Gemini 2.5 Pro call with the strict mutation prompt + diff validation |
| 6 | `qa_agent/main.py` `_run_audit` | writes ADK events to in-memory job state | parses the final agent message into the structured delta-report schema |
| 7 | `scripts/seed_phoenix.py` | prints a manifest | calls Phoenix Python client (or MCP) to upsert judge prompts, the SUT seed prompt, and the dataset examples |
| 8 | frontend | not scaffolded yet | Next.js + shadcn/ui + Tailwind; SSE live-thinking + embedded Phoenix iframe + final delta table |
| 9 | `infra/Dockerfile` | not scaffolded yet | python:3.12-slim + Node 18+ (for npx Phoenix MCP) |

## Estimated remaining work to demo-able state

Person-hours, assuming Phoenix Cloud account is in hand and Vertex AI is unblocked. "Demo-able" = the 3-minute demo in `demo-script.md` runs end-to-end against a live Phoenix Cloud workspace.

| Workstream | Hours |
|---|---|
| Phoenix Cloud account, .env, smoke trace | 1 |
| Phoenix MCP toolset returning real data inside ADK | 3 |
| Real `run_scenario` (ADK driver + SUT loop) | 5 |
| Real Gemini judges (Gemini-only, Phoenix experiment writes, replicas) | 5 |
| Cluster + mutate real Gemini calls | 3 |
| Scenario set expansion from 10 → 50 in Phoenix | 4 |
| End-to-end loop with measurable delta on a real run | 4 |
| Next.js frontend (live thinking + embedded Phoenix + delta table) | 10 |
| Dockerfile + Cloud Run deploy + Secret Manager binding | 3 |
| Pre-recorded "live" audit run + caching layer for the demo | 3 |
| Demo polish, narration, video edit | 6 |
| Devpost writeup + Apache-2.0 LICENSE check | 2 |
| Buffer (one full day of unknowns) | 8 |
| **Total** | **~57 hours** |

For comparison the original Mystery Shopper scaffold sized this at ~54 hours but missed the self-improvement loop entirely. We added ~7 hours of self-improvement work and traded ~4 hours of voice/multi-target adapter work for it. Net ~3 hours and a far stronger thesis.

## Top three risks (refreshed)

1. **Phoenix MCP `upsert-prompt` via `npx` subprocess in Cloud Run.** ADK's `McpToolset` spawns `@arizeai/phoenix-mcp@latest` over stdio. Cloud Run can run sidecar processes but spawning `npx` at request time is unusual; cold-start latency could be brutal. Mitigation: pin the package and pre-warm in the container image, OR fall back to the Phoenix REST API for `upsert-prompt` while keeping MCP for read-mode tools. The demo's "meaningful MCP" criterion is still hit via `list-traces`, `get-spans`, etc. Time at risk: ~3 hours of integration work.

2. **Judge variance reorders the leaderboard.** Same risk the original scaffold flagged; even worse here because the demo's punch comes from a clean before/after delta. If post-fix scores are within IQR of baseline, the demo flops. Mitigation: N=3 replicas, report median + IQR, target the prompt fix on the *most* stable dimension (hallucination, in our internal tests). If we have time on Day 8 we run 200 baseline judge calls across the 50 scenarios and pre-compute per-dimension variance so we know which dimension to feature in the demo.

3. **Self-improvement actually fails to improve.** The QA agent's mutation could break a different dimension while fixing the targeted one. Mitigation: the `mutate_sut_prompt` tool enforces *additive-only* edits, and the QA agent's instruction tells it to flag any dimension that regresses > 0.05. We can show this honestly in the demo ("hallucination -23 points, empathy unchanged") rather than pretending every fix is free.

## Decision gates (recap from build-plan)

- **End of Day 5 (Sat May 30)**: Tech self-score must be ≥ 6 with a real baseline experiment in Phoenix. If not, drop multi-cycle stretch, lock single-cycle for the demo.
- **End of Day 10 (Thu Jun 4)**: All four self-scores must be ≥ 7. If any are below, cut frontend polish first, demo recording polish second.
- **End of Day 13 (Sun Jun 7)**: demo recording must be in the can. After this we don't add features.

## What we kept from the prior scaffold

- **The six judge prompts** (`judge_prompts.py`). These are 80% of the scoring methodology; rewriting them would be waste.
- **The ten seed scenarios** (`scenarios.py`). Three map directly to the SUT's planted pathologies; the other seven cover dimensions we still score.
- **The framing of LLM-as-judge variance as a first-class concern**, not a footnote.
- **Apache-2.0 licensing** and the "Phoenix is the canonical record" architectural posture.

## What we removed

- **The Python `mcp.ClientSession` boot path.** It hides MCP behind Python code; ADK's `McpToolset` exposes it to the agent as first-class tools, which is the correct pattern for the partner's criterion of "the agent can introspect its own observability data at runtime".
- **The target-adapter layer** (HTTPS chat, voice, WebSocket adapters). We audit a single in-repo Gemini SUT now; no third-party endpoint dependency, no rate-limit risk.
- **The "Marriott/Hilton/Hyatt/IHG" framing in the demo.** Replaced with VelvetMint (our own fake DTC brand) so the demo is reproducible by reviewers and has zero TOS exposure.
