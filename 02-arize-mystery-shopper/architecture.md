# Architecture — Self-Improving QA Agent

## Goals

1. **Audit** another Gemini agent end-to-end against a versioned scenario suite, with every turn auto-traced into Arize Phoenix.
2. **Judge** each conversation across six dimensions with reproducible LLM-as-judge experiments (Gemini-only, per hackathon rules).
3. **Introspect** the agent's own failure traces at runtime via Phoenix MCP — read failures, cluster them, generate a fix hypothesis.
4. **Mutate** the SUT's system prompt and dataset examples — write the new prompt version into Phoenix, re-run the experiment, surface the score delta.
5. **Stay in-rules.** Gemini-only AI, Apache-2.0 licensed, hosted on Cloud Run.

## High-level system

```
+-------------------------------------------------------------------------+
|                         User / Operator (browser)                       |
|     POST /audit  { sut_id, scenario_set, mode }                          |
+-----------------------------+-------------------------------------------+
                              |
                              v
+-----------------------------+-------------------------------------------+
|                FastAPI app on Cloud Run                                 |
|   - POST /audit            kick off an audit job                        |
|   - GET  /audit/{id}/events SSE stream of QA-agent thinking            |
|   - GET  /audit/{id}/report final delta report (HTML + JSON)            |
+--+-----------------+---------------------+------------------------------+
   |                 |                     |
   |                 v                     v
   |        +-----------------+   +------------------------------------+
   |        |   QA Agent      |   |  SUT  (Gemini 2.5 Flash, ADK)      |
   |        |   ADK +         |   |  VelvetMint customer-support agent |
   |        |   gemini-2.5-pro|   |  Deliberately flawed (3 pathologies)|
   |        |                 |   |  Domain tools (order_lookup, etc.) |
   |        |   FunctionTools |   +------------------------------------+
   |        |    run_scenario |                  ^
   |        |    cluster_*    |   driven by run_scenario, each turn
   |        |    mutate_sut   |   auto-traced by OpenInference
   |        |                 |
   |        |   McpToolset    |
   |        |    @arizeai/    |---calls Phoenix MCP at runtime
   |        |    phoenix-mcp  |   for traces/datasets/prompts/experiments
   |        +-----------------+
   |
   v
+-------------------------------------------------------------+
|  Arize Phoenix Cloud                                        |
|  (datasets, prompts, experiments, traces, sessions)         |
+-------------------------------------------------------------+
```

## Component responsibilities

### QA Agent (root_agent, Gemini 2.5 Pro via ADK)

The brain of the demo. Its instruction is roughly: *"You are the QA engineer for the VelvetMint customer-support agent. Run the test suite, identify failure clusters from Phoenix traces, propose a single targeted fix to the SUT's system prompt, push the new prompt version, re-run the suite, and report the score delta. Your work product is the Phoenix workspace."*

It has three categories of tools:

1. **Domain tools** (`FunctionTool` wrappers): `run_scenario`, `cluster_failures`, `mutate_sut_prompt`, `run_experiment`.
2. **Phoenix MCP tools** (`McpToolset` over `@arizeai/phoenix-mcp@latest`): the entire Phoenix CRUD surface as runtime tools. The agent picks which to call when.
3. **Built-in ADK affordances**: tool-call streaming, session memory.

We pick ADK (not raw `google-cloud-aiplatform` or low-code Agent Builder) because:

- The Arize partner page explicitly requires a **code-owned runtime** so the agent can be instrumented.
- ADK gives us `McpToolset` for free, which is the cleanest way to expose Phoenix MCP at runtime.
- The [canonical Arize reference repo](https://github.com/Arize-ai/gemini-hackathon) uses ADK + OpenInference + `phoenix.otel.register(auto_instrument=True)`; we want our stack to look like the reference, not invented elsewhere.

### Subject Under Test (SUT, Gemini 2.5 Flash via ADK)

A separate ADK agent. Its only job is to be a believable, deliberately-flawed customer-support agent for the VelvetMint DTC brand. Domain tools (mock VelvetMint domain): `lookup_order`, `lookup_customer`, `issue_refund`, `escalate_to_human`. These are stubbed deterministically against the `synthetic-data/` corpus.

The SUT's *initial* system prompt is intentionally bad in three specific ways:

1. **Hallucinates a fictional "90-day price-match guarantee" policy.** Tested by the `hallucination-bait-policy` scenario.
2. **Drops Spanish code-switches.** Always replies in English even when the user code-switches; doesn't acknowledge `por favor`. Tested by `accent-spanish-en`.
3. **Tries to resolve fraud in-channel** instead of escalating. Tested by `escalation-fraud`.

Each pathology is one or two lines in the SUT's instruction. After the QA agent runs the self-improvement loop, the new prompt version should fix at least one of them without breaking the others. That's the demo's payoff beat.

### Phoenix tracing layer

Configured **once** in `qa_agent/instrumentation.py`:

```python
from phoenix.otel import register

register(
    project_name=os.environ.get("PHOENIX_PROJECT_NAME", "self-improving-qa-agent"),
    batch=False,
    auto_instrument=True,
    verbose=False,
)
```

`auto_instrument=True` plus `openinference-instrumentation-google-adk` means every ADK call, every Gemini call, every tool call (including MCP calls) is a span with no per-call boilerplate. Sessions are tagged with the audit job id + scenario id so the judge can pull a full session back by id.

Both the QA agent and the SUT trace into the same Phoenix project. They show up as distinct agents because OpenInference attaches `openinference.agent.name` automatically.

### Phoenix MCP integration (the critical design choice)

ADK exposes any MCP server as a toolset via `McpToolset`:

```python
from google.adk.tools.mcp_tool import McpToolset, StdioServerParameters

phoenix_tools = McpToolset(
    server_params=StdioServerParameters(
        command="npx",
        args=[
            "-y", "@arizeai/phoenix-mcp@latest",
            "--baseUrl", os.environ["PHOENIX_COLLECTOR_ENDPOINT"],
            "--apiKey",  os.environ["PHOENIX_API_KEY"],
        ],
    ),
)

root_agent = Agent(
    model="gemini-2.5-pro",
    name="qa_agent",
    instruction=QA_INSTRUCTION,
    tools=[
        FunctionTool(func=run_scenario),
        FunctionTool(func=cluster_failures),
        FunctionTool(func=mutate_sut_prompt),
        phoenix_tools,
    ],
)
```

This is the load-bearing line of the entire submission. It means Gemini 2.5 itself, mid-reasoning, can call `list-traces`, `get-spans`, `upsert-prompt`, etc. as natural tool calls — not as Python-side code we wrote. The "agent introspects its own observability data at runtime" claim in the demo script is literally true at the tool-call level, not a metaphor.

We also expose the same Phoenix MCP in `.gemini/settings.json` so that a developer running Gemini CLI from the repo root inherits the same tool surface. That's the "no-code re-runnable methodology" affordance the demo highlights.

### Judge runner

After each scenario run completes, the QA agent reads the session via `get-session`, then calls Gemini 2.5 with each of the six judge prompts (resolved via `get-latest-prompt` so we always use the live version). Each call returns `{"score": float, "rationale": str}`. The result writes back as an experiment row in Phoenix.

Variance handling: each judge call runs N=3 times, we report median + IQR. Variance per dimension is itself published in the report so reviewers see we're honest about LLM-as-judge noise.

### Self-improvement loop

The QA agent's outer loop (driven by its system prompt, not hard-coded Python) does:

1. `run_experiment(version="baseline")` — runs all 50 scenarios through the SUT, scores them.
2. Pulls failing rows: `get-experiment-by-id` → filter where any dimension < 0.5.
3. Calls `cluster_failures(experiment_id)` — Gemini 2.5 reads the rationales and groups them into 1–3 failure modes.
4. Calls `mutate_sut_prompt(cluster_summary)` — Gemini 2.5 proposes a minimal-diff system-prompt edit for the SUT.
5. `upsert-prompt(name="sut-velvetmint-support", template=<new>)` — Phoenix records the new version.
6. `run_experiment(version="post-fix")` — re-runs all 50 scenarios with the new SUT prompt.
7. Compares experiments. Reports per-dimension delta + which scenarios newly pass.
8. (Stretch) For any new failure modes discovered, `add-dataset-examples` to grow the dataset.

Each step is a tool call. The "thinking" stream judges see is the QA agent narrating its plan: *"I see 11 of 50 scenarios failed. Top cluster: hallucinated policies. Proposed edit: add 'never invent policies that are not in your tools' to system prompt. Pushing version v2. Re-running…"*

### Report generator

Aggregates the two experiments into:

- Per-dimension table: score v1 vs v2, delta, p-value (Wilcoxon over the 50 paired scenarios).
- Failure-mode summary: cluster → root cause → prompt edit → which scenarios it fixed.
- Deep link to the Phoenix experiment view for full reproducibility.

## Data model

```
AuditJob
  id, created_at, sut_id, scenario_set_id, status
  -> Run (one per (scenario, sut_prompt_version))
       id, scenario_id, sut_prompt_version, phoenix_session_id
       -> JudgeScore (one per dimension)
            dimension, score, rationale, judge_prompt_version, replica_idx
  -> ImprovementStep
       baseline_experiment_id, fix_experiment_id,
       cluster_summary, prompt_diff, delta_per_dimension
```

Persisted only ephemerally in the FastAPI process for the demo; canonical record is the Phoenix workspace. Post-MVP this moves to Firestore for durability.

## Sequence — one audit + improvement run

```
1.  Client            POST /audit { sut_id }
2.  FastAPI           create AuditJob, return 202 + job_id
3.  Background        boot ADK runner with QA agent
4.  QA agent          tool: phoenix.list-datasets        (find scenario set)
5.  QA agent          tool: phoenix.get-dataset-examples (50 scenarios)
6.  QA agent          tool: run_scenario(s1, sut_id)     (50x)
7.    SUT             driven by Gemini 2.5 Flash, traced
8.  QA agent          tool: run_experiment(baseline)     (writes Phoenix experiment)
9.  QA agent          tool: phoenix.get-experiment-by-id (read failure rows)
10. QA agent          tool: phoenix.get-spans            (deep-dive 3 failing sessions)
11. QA agent          tool: cluster_failures             (Gemini 2.5 clusters rationales)
12. QA agent          tool: mutate_sut_prompt            (proposes a diff)
13. QA agent          tool: phoenix.upsert-prompt        (new SUT prompt version)
14. QA agent          tool: run_scenario(s1, sut_id)     (50x with new prompt)
15. QA agent          tool: run_experiment(post-fix)
16. QA agent          tool: phoenix.add-dataset-examples (new scenarios from failures)
17. QA agent          final: report with score delta
18. Client            GET /audit/{id}/report
```

## Non-goals (MVP)

- **No voice.** Voice agents are tested by their HTTPS-fronted equivalents. Real telephony is out of scope.
- **No human-in-the-loop relabeling.** Phoenix already supports annotations; we don't reinvent.
- **No production CI hook.** The agent's report would slot into a GitLab MR comment or GitHub Action; we document the design but don't ship the integration in the 16 days.

## Open questions

- **Iteration cap.** The agent could loop forever in principle. MVP: hard-stop after one full improvement cycle (baseline → fix → verify). Multi-cycle is a stretch.
- **Stable scoring across runs.** LLM-as-judge has variance. Mitigation: N=3 replicas per judge call, report median + IQR, surface per-dimension variance in the report so reviewers see we measured it. Cost: ~3x judge spend but the audit budget bounds it.
- **Cost.** Baseline 50 scenarios × ~6 turns × 2 LLM calls (SUT + driver) ≈ 600 calls. Judge: 50 × 6 dims × 3 replicas = 900 calls. Then the same for the post-fix run = ~3000 calls total. At Gemini 2.5 Flash pricing this is bounded; we'll surface the per-audit cost in the report.
