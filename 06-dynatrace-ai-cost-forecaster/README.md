# Track 6: Dynatrace — Production AI Cost Forecaster (one-pager)

> **This is a pivot backup, not a primary build.** Strong idea but tedious to set up.

## One-liner
*"Your LLM costs are quietly killing your runway. This agent predicts your end-of-month bill, finds the cost spike before you see the invoice, and opens a fix."* — Uses Dynatrace's underused timeseries forecasting + changepoint detection on LLM token-usage telemetry to predict cost overruns before they happen.

## Why Dynatrace
Most Dynatrace hackathon submissions will be variants of "AI postmortem agent" or "AI incident responder" — terrain so crowded the judges (Sean O'Dell, Jeff Blankenburg) will see 100+ of them. This one uses Dynatrace's **actually-underused** features:
- `Forecasting Agent` (statistical timeseries forecasting on any metric)
- `Changepoint Agent` (finds outliers + significant trends)
- `Davis Copilot` for the deep-dive RCA

And applies them to a new domain: **AI economics**, not IT ops. That's a category Dynatrace doesn't own yet.

## Partner integration points
- Ingest LLM token-usage telemetry via OpenLLMetry → Dynatrace Grail
- `execute_dql` for token-usage queries
- `Forecasting Agent` for end-of-month bill projections
- `Changepoint Agent` for spike detection
- `chat_with_davis_copilot` for the LLM-side RCA on cost spikes
- `send_slack_message` for proactive alerts
- `create_dynatrace_notebook` for shareable reports

## Architecture (rough)
```
LLM apps emit OpenLLMetry traces → Dynatrace Grail
  Cloud Scheduler (hourly) → Cloud Function → Agent
     1. Query Dynatrace for last 30 days of token usage by model/endpoint
     2. Run forecasting → projected end-of-month spend
     3. Run changepoint analysis → spike detection
     4. For each spike, drill into traces: which endpoint, which prompt, why
     5. If spike unexplained: Davis Copilot consult
     6. Open GitLab issue with proposed prompt-fix or rate-limit change
     7. Slack alert to AI infra team
Output: dashboard + GitLab issue + Slack message
```

## Demo flow (3 min)
- 0:00–0:15: Hook — "Last month we got a $40K Bedrock bill. We didn't know until the invoice. Watch this."
- 0:15–0:45: Dashboard shows a fake company's normal AI usage. A "bad deploy" introduces a 100x token-usage prompt regression.
- 0:45–1:45: Agent reasoning streams: forecasting shows projected end-of-month spend going from $4K → $47K. Changepoint detects spike at deploy time. Drills into the prompt that changed. Identifies the regression.
- 1:45–2:30: Agent opens a GitLab issue with the fix. Slack message goes out. Updated forecast: $4.2K (back to normal).
- 2:30–3:00: Tagline + tech stack.

## Why this is our backup, not primary
- **Simulating convincing LLM telemetry into Dynatrace is tedious** — we'd write a fake instrumentation harness, not use real production data
- **Audience is narrower** (AI infra teams, not all engineering)
- **The pain is real but not yet "household"** — many judges may not have personally felt a $40K LLM bill (yet)

## When to pivot to this
- If we have time pressure and a smaller demo footprint helps
- If we get free Dynatrace credit and the platform feels fast to work with

## Estimated build effort
- 3 days Dynatrace setup + OpenLLMetry instrumentation of a fake LLM service
- 7 days agent + forecasting + changepoint logic + RCA flow
- 4 days polish + video
- 5 days buffer

Doable in 19 days.

## Honest weakness
Simulated telemetry feels simulated to judges. We'd need to make the fake LLM service feel real — multiple endpoints, realistic usage patterns, an actual deployable Python service emitting real OpenTelemetry traces.

## Bonus angle
The judges *building agents for this very hackathon* personally feel this pain — surprise AWS Bedrock / Vertex AI bills are a 2026 board-level concern. That's a free emotional vote if the demo lands.
