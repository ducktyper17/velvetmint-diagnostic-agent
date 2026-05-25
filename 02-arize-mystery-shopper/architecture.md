# Architecture — Voice-AI Mystery Shopper

## Goals

1. Drive realistic multi-turn conversations against an arbitrary third-party AI agent (chat URL, voice phone number, or HTTP API).
2. Record every turn as a Phoenix trace/session so failures are inspectable, not just summarized.
3. Score each conversation with reproducible LLM-as-judge experiments across six dimensions.
4. Produce a competitive-intelligence report comparing targets head-to-head.

## High-level system

```
+-----------------------------------------------------------------------+
|                         User / Operator (browser)                     |
|     POST /audit  { targets: [...], scenario_set: "default-50" }       |
+-----------------------------+-----------------------------------------+
                              |
                              v
+-----------------------------+-----------------------------------------+
|                   FastAPI app on Cloud Run                            |
|   - /audit            kick off an audit job                           |
|   - /audit/{id}       poll status, stream events                      |
|   - /audit/{id}/report   final competitive-intelligence report       |
+--+-----------------+---------------------+----------------------------+
   |                 |                     |
   | drives          | logs spans          | runs experiments
   v                 v                     v
+--------------+  +----------------+  +---------------------------------+
|  Target AIs  |  | Phoenix tracer |  | Phoenix MCP server              |
|  (under test)|  | (OTel exporter)|  | (@arizeai/phoenix-mcp)          |
|              |  |                |  |                                 |
|  chat HTTP   |  |                |  |  list-datasets / get-dataset    |
|  voice gw    |  |                |  |  add-dataset-examples           |
|  custom API  |  |                |  |  list-experiments-for-dataset   |
+--------------+  +----------------+  |  get-experiment-by-id           |
                                      |  list-prompts / upsert-prompt   |
                                      |  list-traces / get-spans        |
                                      +----------------+----------------+
                                                       |
                                                       v
                                            +----------+----------+
                                            |  Arize Phoenix      |
                                            |  (cloud or local)   |
                                            +---------------------+
```

## Component responsibilities

### Orchestrator agent (Gemini 3 via Vertex AI)

The "customer" in every test conversation. Reads a `Scenario` (persona, opening message, intent, escalation triggers) and drives a multi-turn dialog with the target AI. Why an LLM and not a static script: the target AI's response is unpredictable, so the test customer must improvise to keep the scenario realistic without going off-script. Constraints are encoded in the scenario's `stop_when` conditions so a conversation can't run forever.

### Target adapter layer

A small set of adapters that normalize the "send a message, get a response" surface across:

- HTTPS chat endpoints (most modern bots)
- WebSocket chat (Intercom-style)
- Voice phone numbers via a telephony gateway (Twilio / Vapi) and STT/TTS
- Custom REST APIs

The MVP ships only the HTTPS chat adapter. Voice is a stretch goal.

### Phoenix tracer

The orchestrator process is OTel-instrumented via the `arize-phoenix` Python SDK. Every LLM call, target-AI call, and judge call becomes a span. Each scenario run is a session (`session.id` attribute set to the audit-job id + scenario id). This is what makes the report drill-downable: clicking a failed cell in the report deep-links to the Phoenix session view.

### Phoenix MCP server

Talks to Phoenix on behalf of the agent for dataset/experiment/prompt operations. We use the MCP server rather than the Python SDK directly for these operations because:

1. It standardizes the agent's tool surface (Gemini 3 calls MCP tools like any other tool).
2. It version-controls our judge prompts as first-class Phoenix objects.
3. Experiments registered through MCP show up in the Phoenix UI immediately — reviewers can re-run them.

We still use the Phoenix Python SDK for OTel tracing (low-level span writes) because that path is too hot for MCP overhead.

### LLM-as-judge

After each scenario run completes, the judge process pulls the trace for that session and scores it on six dimensions. Each (scenario, dimension) pair becomes one row in a Phoenix experiment. The judge prompt for each dimension is fetched from Phoenix via `get-latest-prompt` so the methodology is reproducible — if we tune a rubric, the new version is logged and existing scores stay tied to the old version.

### Report generator

Aggregates experiment results into a head-to-head table per target plus a per-dimension narrative. MVP renders HTML server-side; PDF is post-MVP via headless Chrome.

## Data model

```
AuditJob
  id, created_at, targets[], scenario_set_id, status
  -> ScenarioRun (one per target x scenario)
       id, target_id, scenario_id, phoenix_session_id, transcript[]
       -> JudgeScore (one per dimension)
            dimension, score, rationale, judge_prompt_version
```

`ScenarioRun.transcript` is denormalized for speed; the canonical record is the Phoenix session.

## Sequence — one audit run

```
1.  Client                 POST /audit { targets, scenario_set }
2.  FastAPI                create AuditJob row, return 202 + job_id
3.  Worker                 for each (target, scenario) pair:
4.    Orchestrator           Gemini 3 turn-by-turn: customer says X
5.    Target adapter         POST to target, await response
6.    Phoenix tracer         emit span: target.response (latency, content)
7.    loop until scenario.stop_when satisfied
8.  Judge runner           pull session from Phoenix
9.    for each dimension     LLM-as-judge call, write JudgeScore
10.   write experiment row to Phoenix
11. Report                  aggregate scores, render HTML
12. Client                  GET /audit/{id}/report
```

## Non-goals (MVP)

- **No real voice.** Phone/voice agents are tested by their HTTPS-fronted equivalents (every voice vendor exposes a debug endpoint). Real telephony is post-MVP.
- **No legal review of TOS.** Demo uses sandbox or self-owned bots. Pointing this at a competitor in production is the buyer's responsibility — we surface that prominently in the UI before any external call.
- **No human-in-the-loop relabeling.** The Phoenix UI already supports annotation; we don't reinvent it.

## Open questions

- **Rate limiting against targets.** A 50-scenario run against a real target is ~50 multi-turn conversations. We need per-target backoff so we look like a single tester, not a DDoS. MVP: hardcoded 1 conversation/sec/target, configurable.
- **Stable scoring across runs.** LLM-as-judge has variance. Phoenix experiment runs help us measure it; we'll publish judge variance per dimension in the demo so reviewers see we're honest about it.
- **Cost.** 4 targets x 50 scenarios x ~8 turns x 2 LLM calls per turn (customer + judge) ≈ 3,200 calls per audit. At Gemini 3 pricing this is bounded but worth tracking; the report will surface the per-audit cost.
