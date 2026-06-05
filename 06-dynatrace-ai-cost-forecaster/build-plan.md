# Dynatrace build plan — Agent Reliability Guard

## Demo contract
By the end of this build, we must be able to show:

1. a Gemini-powered app on Google Cloud emitting real telemetry
2. a deliberate regression after a prompt/tool/deploy change
3. a guard agent using the Dynatrace MCP to detect and explain the regression
4. a Dynatrace notebook and alert created from the findings

If any step above is missing, the story is weaker.

## The shortest path to something judges believe
Do not start with a broad platform. Start with one narrow workflow that can fail in a vivid way.

Recommended demo app:

- **Customer support assistant** with 2-3 tools:
  - `lookup_order`
  - `refund_check`
  - `handoff_to_human`

Recommended bad deploy:

- prompt version causes repeated `refund_check` calls on ambiguous requests
- responses become slower
- token use spikes
- tool errors rise

That gives us four observable signals with one controlled bug.

## Build order
### Day 1: access and ingestion
- Create Dynatrace trial
- Verify Agent Platform / Gemini path on GCP
- Get one app sending OTel traces, metrics, and logs into Dynatrace
- Add version attributes we can filter on later:
  - `prompt_version`
  - `tool_name`
  - `release_id`
  - `route`
  - `model`

**Exit criterion:** we can see at least one full request trace in Dynatrace.

### Day 2: create the regression
- Implement healthy and broken variants of the app
- Produce repeatable traffic for both versions
- Confirm the regression is visible in telemetry:
  - higher token count
  - slower latency
  - more tool calls
  - more failures or retries

**Exit criterion:** the two versions are distinguishable by DQL.

### Day 3: query and explain
- Wire the Dynatrace MCP into the guard agent
- Build the DQL queries for:
  - token usage by release
  - latency by route and release
  - error rate by tool
  - top failing traces / spans
- Add the agent prompt so it explains:
  - what changed
  - who is affected
  - why it is likely happening

**Exit criterion:** one prompt to the guard agent returns a useful written diagnosis.

### Day 4: analyzers and forecasting
- Use `list_davis_analyzers`
- Run changepoint / anomaly detection on the regression window
- Run forecasting on token burn or latency trend
- Capture the result in a concise summary sentence

**Exit criterion:** the agent can say both "a regression started here" and "if ignored, this is the likely impact."

### Day 5: operational action
- Create a Dynatrace notebook with:
  - summary
  - evidence
  - screenshots or linked charts
  - recommended fix
- Send Slack or workflow notification

**Exit criterion:** there is a shareable artifact and an action taken.

### Day 6: UI and narration
- Add a minimal frontend to stream the agent's reasoning
- Show:
  - healthy baseline
  - bad deploy
  - investigation
  - notebook / alert output

**Exit criterion:** the full 3-minute story runs end to end.

### Day 7+: polish
- tighten copy
- reduce latency
- improve visual pacing
- rehearse video
- record 5-10 stable demo traces for fallback replay mode

## Required telemetry fields
Make sure these are attached from the start:

- `prompt_version`
- `release_id`
- `tool_name`
- `tool_status`
- `route`
- `user_intent`
- `model_name`
- `input_tokens`
- `output_tokens`
- `request_latency_ms`

If these tags are missing, the root-cause story gets fuzzy.

## Core DQL questions we need answered
- Which release introduced the regression?
- Which route or intent got worse?
- Which tool started failing or retrying?
- How much did tokens per request increase?
- What is the projected cost if this stays live?

## Nice-to-have after MVP
- compare two releases automatically
- add release markers or deployment annotations
- add rollback recommendation text
- add a "blast radius" score combining cost, latency, and failure rate
- add a cached demo replay mode for judging reliability

## Risk management
### Risk: Dynatrace setup friction
Mitigation: use the instrumentation examples immediately; do not invent telemetry plumbing from scratch.

### Risk: no clean forecasting signal
Mitigation: keep forecasting as a supporting metric, not the only source of drama.

### Risk: the demo looks like a dashboard, not an agent
Mitigation: make the notebook creation and notification step mandatory in the demo.

### Risk: too many moving pieces
Mitigation: one app, one regression, one investigation loop.

## Submission framing
Use language like this in the Devpost writeup:

> We built a Gemini-powered guard agent that observes other Gemini agents in production via Dynatrace, detects regressions from real OpenTelemetry telemetry, explains the root cause with Davis intelligence, and publishes an operator-ready incident notebook.

That makes the partner contribution impossible to miss.
