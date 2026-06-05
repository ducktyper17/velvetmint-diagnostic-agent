# Track 6: Dynatrace — Agent Reliability Guard

> This is the stronger Dynatrace path. Keep cost forecasting, but demote it from "the whole product" to one proof point inside a bigger, more demoable story.

## One-liner
*"Your Gemini agent looked healthy in staging. In production it got slower, more expensive, and started misusing tools. This guard agent catches the regression, explains the root cause, forecasts the burn if you ignore it, and ships a shareable incident notebook in minutes."*

## Why this is the winning Dynatrace angle
The official Dynatrace track resources are not about generic incident response. They are about **observability for AI agents themselves**:

- OpenTelemetry traces, metrics, and logs for Agent Platform / Gemini workloads
- token spend, tool calls, latency, and errors
- DQL over live runtime data
- Davis intelligence for explanation
- analyzers for forecasting and changepoint detection
- workflows, Slack notifications, and notebooks for actionability

That means our submission should look like **"an agent that watches agents"**, not a generic SRE assistant with Dynatrace bolted on.

## Core thesis
Most teams will show a chatbot with a dashboard. We should show a **production safety system for Gemini agents**:

1. A real Gemini-powered app runs on Google Cloud and emits OTel telemetry.
2. A bad prompt/tool/model change causes a visible regression.
3. Our guard agent uses the Dynatrace MCP to detect the regression, explain it, and publish the evidence.
4. The agent produces an operator-ready output: a Dynatrace notebook, alert, and remediation recommendation.

This hits all four judging buckets:

- **Tech**: deep Dynatrace MCP + Google Cloud + real telemetry
- **Design**: clear "before vs after deploy" story with streamed reasoning
- **Impact**: every AI team is scared of silent regressions
- **Idea**: meta-agent for agent reliability is more memorable than another "incident copilot"

## What changed from the old cost-forecaster idea
The original idea had a good insight but the wrong center of gravity:

- **Old center**: "forecast my end-of-month AI bill"
- **New center**: "catch and explain AI agent regressions before they burn money and trust"

This is better because:

- it matches the Dynatrace resource page exactly
- it uses more of the MCP surface area, not just forecasting
- the demo can use **real telemetry from our own app**, not a purely synthetic finance dashboard
- forecasting becomes a strong supporting move instead of the whole story

## Product concept
### Name
**Agent Reliability Guard**

### User
AI engineer / platform engineer / developer owning a Gemini-powered production workflow.

### Problem
Prompt edits, tool-schema changes, model swaps, or routing bugs can quietly cause:

- token burn explosions
- latency spikes
- retry loops
- tool-call failures
- bad handoffs between agent steps

Teams usually learn this from a user complaint, a slow dashboard, or a surprise bill.

### What the agent does
1. Watches Dynatrace telemetry from a Gemini app instrumented with OpenTelemetry.
2. Detects a changepoint after a release or config change.
3. Queries DQL for the exact regression slice: token usage, latency, tool errors, affected routes, prompt/tool version.
4. Runs Davis analyzers to forecast the cost/latency impact if nothing changes.
5. Uses Davis Copilot to turn raw telemetry into a concise explanation.
6. Creates a Dynatrace notebook with evidence, charts, and remediation notes.
7. Sends a Slack notification or workflow event for the owner.

## Resource-to-build mapping
Use the official Dynatrace track resources directly instead of treating them as optional reading:

- **Sign Up for Dynatrace**: Day 1, create the tenant and verify we can ingest telemetry.
- **Dynatrace for Agent Platform**: primary path for observing Agent Platform / Gemini workloads.
- **Instrumentation Examples (GitHub)**: fastest route to exporter config, dashboards, and sample OTel wiring.
- **Bindplane (Google Edition)**: fallback if direct OTel export is annoying or we want to route multiple telemetry streams cleanly.
- **AI Coding Agent Monitoring**: useful during development to observe our local build/test loop, but not required in the final demo.
- **Dynatrace for Gemini Enterprise**: optional only; do not make this a dependency for the hackathon build.
- **Dynatrace MCP Server**: the required partner integration and our main action surface.

## MCP tool plan
The demo should visibly use these Dynatrace capabilities:

- `execute_dql`: fetch token, latency, trace, span, and error slices
- `generate_dql_from_natural_language`: speed up query authoring during development
- `list_davis_analyzers` + `execute_davis_analyzer`: run forecasting and changepoint detection
- `chat_with_davis_copilot`: summarize probable root cause in operator language
- `create_dynatrace_notebook`: produce the artifact judges can see and trust
- `send_slack_message` or `create_workflow_for_notification`: prove the agent takes operational action

## Architecture
```text
Gemini app on Cloud Run / Agent Platform
  -> OpenTelemetry spans, metrics, logs
  -> Dynatrace
       -> token usage
       -> tool calls
       -> latency
       -> errors
       -> release markers / prompt version tags

Guard Agent (Agent Builder + Gemini)
  1. Triggered by schedule or release marker
  2. Query Dynatrace with DQL
  3. Detect changepoint / anomaly
  4. Forecast blast radius if ignored
  5. Ask Davis for RCA narrative
  6. Publish notebook
  7. Send Slack/workflow notification
```

## The demo we should actually build
### Scenario
Build a small Gemini-powered customer-support or ops assistant with two versions:

- **healthy version**: normal prompt, sane tool usage
- **bad deploy**: prompt/tool bug that causes repeated tool calls, higher tokens, slower responses, and more failures

### Why this scenario works
- It produces **real OTel telemetry**
- It creates a dramatic before/after change
- It lets Dynatrace shine on the exact signals their resource page calls out
- It avoids needing a giant synthetic data story

## Three-minute video flow
- **0:00–0:15**: Hook. "AI agents rarely fail all at once. They get slower, more expensive, and quietly worse. Watch us catch that in minutes."
- **0:15–0:40**: Show the Gemini app working normally.
- **0:40–1:00**: Introduce the bad deploy or prompt change.
- **1:00–1:45**: Guard agent wakes up. It queries Dynatrace, finds the changepoint, shows token and latency regression, and forecasts the cost if the issue stays live.
- **1:45–2:20**: Agent explains the likely root cause in plain English: "Prompt v12 created a tool retry loop on refund requests."
- **2:20–2:40**: Dynatrace notebook appears with evidence and remediation guidance.
- **2:40–3:00**: Slack/workflow alert lands. Final line: "We turned AI observability into an autonomous reliability workflow."

## MVP scope
Ship the smallest version that still feels real:

- one Gemini app
- one intentional regression
- one DQL-driven investigation flow
- one analyzer call
- one notebook output
- one operational notification

Everything else is polish.

## What not to build
Avoid these traps:

- **Do not** make this a generic "incident responder"
- **Do not** depend on a giant synthetic enterprise environment
- **Do not** overbuild dashboards before the notebook and alert flow works
- **Do not** require GitLab, Slack, or another partner just to make the core story coherent

## Why judges may remember this
- It is about **AI agents**, not just apps in general
- It makes Dynatrace the hero instead of a passive telemetry sink
- It shows a real production pain that hackathon judges personally understand
- It demonstrates agentic behavior with evidence, not just chat output

## If we want one extra punch
Keep the original cost-forecaster move as a secondary reveal:

> "If left running for 7 days, this regression will waste an estimated $3,480 in tokens and add 18 hours of cumulative user wait time."

That gives us the old "AI economics" insight without making it the entire product.

## Repo layout

| Path | Purpose |
|---|---|
| `agent/` | Guard agent (Gemini + Dynatrace MCP), `POST /investigate` SSE API, Dockerfile |
| `demo-app/` | `refund-assistant` workload with OTel spans + healthy/bad modes + traffic generator, Dockerfile |
| `frontend/` | Next.js 14 dashboard: live thinking panel, tool timeline, investigation card |
| `scripts/deploy.sh` | Cloud Run deploy for all 3 services + Secret Manager binding |
| `Makefile` | quickstart (setup / dev / traffic-healthy / traffic-bad / deploy) |
| `build-plan.md` | Day-by-day execution plan |

## Quickstart

```bash
# One-time
make setup

# Three terminals
make demo-app-dev    # http://localhost:8090
make backend-dev     # http://localhost:8080
make frontend-dev    # http://localhost:3000

# Generate before/after telemetry (in a 4th terminal)
cd demo-app && uv run python scripts/traffic.py --mode demo --rps 2 --phase-duration 30
```

Open the frontend at <http://localhost:3000> and press **Investigate**. The
guard agent will query Dynatrace for runtime signals (or stub data if you
set `STUB_DYNATRACE_TOOLS=true`), run change + forecast analyzers, draft a
notebook, and notify the owner — narrating each step live in the panel.

## Deploy to Cloud Run

```bash
# Requires dynatrace-mcp-token in Secret Manager + envs in agent/.env
make deploy
```
