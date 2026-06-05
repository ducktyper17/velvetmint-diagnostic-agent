# Agent Reliability Guard — Devpost draft

> An agent that watches agents. Gemini-powered guard that catches silent regressions in production AI agents using Dynatrace runtime telemetry, explains the root cause, forecasts the burn, and ships an operator-ready notebook in minutes.

## Inspiration

Every team shipping a Gemini agent in 2026 has the same problem: their agent worked fine in staging, but in production it is silently getting slower, more expensive, and quietly worse. Prompt edits, tool-schema changes, and model swaps create regressions that do not crash anything — they just burn tokens and trust. Teams usually find out from a user complaint, a slow dashboard, or a surprise bill at the end of the month.

We wanted to build the safety net we wished we had: a meta-agent whose only job is to watch other agents and call out when something is drifting. The Dynatrace track was the natural home for this — their MCP server gives us DQL over live OpenTelemetry telemetry, Davis analyzers for changepoint detection and forecasting, and notebooks/Slack as a real action surface. Nothing about this story works without real runtime data, and Dynatrace was the only partner that gave us all of it from one integration.

## What it does

Agent Reliability Guard is a Gemini-powered investigation agent that runs as a service. When a regression is suspected — or on a schedule, or on a release marker — it:

1. Queries Dynatrace via the MCP server for the runtime signals of the affected Gemini app: p95 latency, tokens per request, tool error rate, and retry counts, sliced by release ID.
2. Runs the Davis changepoint analyzer to locate the exact boundary where the regression started.
3. Runs the Davis forecasting analyzer to project the cost and latency impact if the issue stays live for a week.
4. Drafts a Dynatrace notebook with the evidence, the probable root cause, and the recommended fix.
5. Sends a Slack-style notification to the on-call channel with a link to the notebook.
6. Returns a structured RCA payload to the dashboard: summary, probable root cause, impact, recommended fix.

The whole investigation streams live to a Next.js dashboard via Server-Sent Events, so the operator watches the agent think — every public thought, every tool call, every tool result, every parallel batch.

The killer demo: we ship a deliberately broken refund-assistant (a second Gemini app) that retries `refund_check` on ambiguous queries. Press one button, and the Guard catches the regression, explains it ("prompt v12 created a tool retry loop"), and tells you it will waste ~$3.4k in tokens and add 18 hours of cumulative user wait time over the next week if you do nothing.

## How we built it

Three services, all written to be demoable from a single laptop.

**Guard agent (`agent/`)** is a FastAPI service that exposes `/investigate` as SSE. The investigation loop is a ReAct controller built around Gemini 2.5 Flash on Vertex AI, with forced function-calling mode and six declared tools mapped to the Dynatrace MCP surface. The interesting design choice: we let the model emit multiple tool calls in one turn, and we fan them out concurrently with `asyncio.gather` — the three read tools (runtime signals, changepoint, forecast) all run in parallel inside one Gemini turn, which is where most of the per-investigation latency lives. Flash was a deliberate pick over Pro: this is a tool-routing task, not a reasoning-heavy one, and the operator feels the per-turn latency directly when they press the button.

**Demo app (`demo-app/`)** is a real Gemini-powered refund-assistant with three tools (`lookup_order`, `refund_check`, `handoff_to_human`), full OpenTelemetry instrumentation, and a healthy/bad mode switch. The bad mode uses prompt v12, which causes `refund_check` to retry on any ambiguous response — this is what produces the actual regression in the telemetry the Guard later investigates. The same release_id, prompt_version, tool_name, route, and user_intent tags are attached to every span, so the Guard's DQL can slice by them later.

**Frontend (`frontend/`)** is a Next.js 14 dashboard with four components: an investigation card, a live thinking panel, a tool timeline, and a release/regression banner. Streaming the SSE through a Next.js API proxy lets us keep the agent URL server-side.

**Replay mode** was the single best decision we made for the demo. `run_replay` in `agent_loop.py` forces both `stub_gemini_responses` and `stub_dynatrace_tools` on, adds human-readable delays between events, and produces a deterministic, paced investigation that is identical every run and cannot fail on stage even with no credentials or connectivity. The whole replay is real SSE through the real pipeline — only the model and Dynatrace calls are stubbed.

## Challenges we ran into

- **MCP parameter shape drift.** The Dynatrace MCP server documents argument names like `query` and `name`, but different builds we tried wanted `dql`, `statement`, `analyzer_name`, or `analyzer_id`. Rather than guess, we wrote `_call_tool_with_fallbacks` in `tools.py` that tries several plausible shapes per tool and uses the first one that succeeds. Brittle in a real production setting, but exactly right for a hackathon where the tenant might differ from ours.
- **Davis analyzer names are tenant-specific.** "Changepoint Agent" and "Forecasting Agent" are conventional display names but not guaranteed. We made them env-overridable and documented where to verify them in the tenant.
- **Parallel tool calls inside one Gemini turn.** Forced function-calling mode (`ANY`) plus disabling automatic function calling lets Gemini return multiple function calls per response, but we had to make sure the ReAct loop did not finalize on a turn that also requested reads — otherwise the model would skip the evidence step.
- **Keeping the demo bulletproof.** Real Dynatrace + Vertex calls during a live recording is a risk multiplier. The replay path was non-negotiable.

## Accomplishments we are proud of

- The Guard is genuinely useful, not a chatbot wrapper. The investigation it runs is the one we would actually want to run by hand at 3am.
- Parallel tool batching inside one Gemini turn cuts investigation latency by roughly the depth of the read fan-out — that is the bulk of the wall clock the operator feels.
- The demo flow tells the full story in 3 minutes without skipping anything: healthy baseline → bad deploy → guard activates → notebook lands → Slack alert → forecast.
- Replay mode means the demo cannot fail on stage. Same SSE pipeline, deterministic data.

## What we learned

- Forced function calling + parallel tool execution in one Gemini turn is the single biggest agent latency win we found, and it works cleanly with the Vertex SDK.
- "Watch one signal" beats "watch everything." The story is dramatically clearer when the agent reports on three named runtime signals (latency, token burn, tool error rate) than when it summarizes a generic dashboard.
- A replay path is worth more than any amount of demo-day prayer. Build it before you need it.
- Dynatrace as an action surface (notebooks + workflows + Slack) is what makes the agent feel autonomous instead of advisory.

## What is next for Agent Reliability Guard

- **Auto-trigger on release markers.** Today the Guard runs on-demand from the dashboard. The natural next step is to subscribe to Dynatrace release events and auto-investigate every deploy of a tagged Gemini app.
- **A library of analyzers.** Add `chat_with_davis_copilot` for narrative explanation, plus tenant-specific anomaly detectors for token spend, tool retry rates, and prompt cache hit ratios.
- **Compare-two-releases mode.** Given release A and release B, the Guard should report exactly what got worse, with the same evidence shape.
- **Auto-remediation.** If the recommended fix is "roll back prompt v12," the Guard should be able to open the PR (via the GitLab MCP) and capture the rollback as a release marker so the next investigation sees a clean recovery.
- **Multi-agent fleets.** One Guard per agent does not scale. The next iteration should investigate any one of N registered services on demand.

## Built with

- Google Cloud Vertex AI (Gemini 2.5 Flash)
- Google Cloud Agent Builder
- Cloud Run for all three services
- Google Cloud Secret Manager for the Dynatrace MCP token
- Dynatrace MCP Server (partner integration)
- Dynatrace DQL, Davis analyzers, notebooks, and workflow notifications
- OpenTelemetry (instrumented inside the demo refund-assistant)
- FastAPI + httpx + tenacity + pydantic
- Next.js 14 + Tailwind (dashboard)
- Server-Sent Events (live agent stream)
- Apache 2.0 license

## Try it out

- **Live demo URL:** _[hosted Cloud Run URL — to be populated]_
- **GitHub:** _[repository URL — to be populated]_
- **Video walkthrough:** _[YouTube unlisted link — to be populated]_

Local quickstart:

```bash
make setup
make demo-app-dev    # http://localhost:8090
make backend-dev     # http://localhost:8080
make frontend-dev    # http://localhost:3000
make traffic-healthy # baseline
make traffic-bad     # introduce the regression
```

Then open the dashboard and press **Investigate**.
