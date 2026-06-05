# Self-Improving QA Agent (Arize track — primary submission)

> **The AI quality engineer that never sleeps.**

> **Status:** Primary submission for the Google Cloud Rapid Agent Hackathon (deadline June 11, 2026). Track: **Arize Phoenix**. The folder is still named `02-arize-mystery-shopper/` to preserve git history; the concept itself has been completely re-aimed (see `DECISION.md` at the workspace root for the May 26 changelog). The previous "Mystery Shopper" framing — auditing competitor AIs — was deprioritized because it didn't hit Arize's stated bonus criterion of "agents that use their own observability data to improve over time."

## One-liner

An autonomous Gemini ADK agent that owns the entire eval methodology for another Gemini agent — runs scenarios, scores them via Phoenix LLM-as-judge, and then **uses its own Phoenix traces to rewrite the system-under-test's prompt and prove a measurable quality improvement, live**, in front of the judges.

## Why this wins

The [Arize partner page](https://rapid-agent.devpost.com/details/arize-resources) calls the shot for us:

> "We'll evaluate submissions based on technical implementation, **meaningful use of tracing and MCP**, **quality of the agent's self-improvement loop**, and overall impact... **Bonus points for agents that use their own observability data to improve over time.**"

This product is the most direct possible expression of those words.

## The problem

Every team shipping a Gemini-based agent in 2026 has the same three problems:

1. **They don't know if their agent is regressing.** Vibes-based testing dominates. CI gates on "did the unit tests pass" not "did empathy drop 8 points compared to last release."
2. **When they do find a regression, root cause is manual.** Engineers scroll through traces in a dashboard.
3. **Fixing it means rewriting prompts by hand.** The loop from "we got worse" to "here's the fix" is days, not minutes.

There is no shipped product in 2026 that closes the full eval → root cause → prompt fix → verify loop autonomously. The closest analogs (Patronus, Braintrust, Promptfoo, Humanloop, Langfuse) are dashboards and harnesses. Humans drive every step.

We make the **agent** the QA engineer.

## The user

Two buyers, same product:

- **AI platform engineers** at companies running 5–50 deployed agents. They want a CI gate that fails the build if any judge dimension regresses, plus an autonomous fix-suggester.
- **AI product managers** who want a "what's the quality of the agent we shipped this morning" answer without filing a ticket.

## How it works

```
                  POST /audit { sut: <gemini-agent-id> }
                          |
                          v
+-------------------------------------------------------------+
| QA Agent  (Google ADK, gemini-2.5-pro)                      |
|                                                             |
|  Tools:                                                     |
|   - run_scenario(scenario_id, sut_id)  — drives one         |
|     scenario through the SUT, traced by OpenInference       |
|   - phoenix.* via @arizeai/phoenix-mcp (McpToolset):        |
|       list-traces, get-spans, list-experiments-for-dataset, |
|       get-experiment-by-id, upsert-prompt,                  |
|       add-dataset-examples, get-latest-prompt               |
|   - cluster_failures(experiment_id) — Gemini-only           |
|     clustering of failure rationales                        |
|   - mutate_sut_prompt(failure_summary) — Gemini proposes    |
|     a system-prompt rewrite for the SUT                     |
|                                                             |
|  Loop:                                                      |
|   1. Pull 50-scenario dataset from Phoenix                  |
|   2. For each scenario: run_scenario against the SUT        |
|      (sessions tagged so the judge can pull them back)      |
|   3. Run Phoenix LLM-as-judge experiment (6 dimensions)     |
|   4. Read failure spans via Phoenix MCP                     |
|   5. Cluster failures, propose prompt rewrite               |
|   6. upsert-prompt new SUT version                          |
|   7. Re-run experiment — write rows linked to the new       |
|      prompt version                                         |
|   8. Surface delta: "hallucination 23% -> 6%"               |
|   9. add-dataset-examples for any new failure modes         |
+-------------------------------------------------------------+
                          |
                          v
        Output: a self-contained Phoenix workspace +
                a delta report the user can defend.
```

The six judge dimensions are: **Empathy, Accuracy, Escalation Appropriateness, Bias / Fairness, Hallucination, Brand Voice**. Each is a versioned Phoenix prompt (`upsert-prompt`) so the eval methodology is itself auditable.

## The Subject Under Test (SUT)

The SUT is **deliberately ours, and deliberately flawed.** It is a Gemini ADK customer-support agent for a fake DTC brand called **VelvetMint** (the synthetic dataset we already built lives in `synthetic-data/`). The SUT ships with three injected pathologies the QA agent must discover:

1. **Hallucinates a fictional "90-day price-match guarantee."** (Hits the `hallucination-bait-policy` scenario.)
2. **Drops the language signal when the customer code-switches to Spanish.** (Hits `accent-spanish-en`.)
3. **Over-apologizes and never escalates fraud claims.** (Hits `escalation-fraud`.)

Why have us own the SUT:

- **No TOS / rate-limit risk** with third-party targets.
- **Demo is deterministic** — same SUT prompt, same scenarios, same scores within judge variance.
- **Score deltas are real and visible.** When the QA agent rewrites the SUT prompt to fix the hallucination, the hallucination scenario actually starts passing.

## Why Phoenix MCP is genuinely load-bearing (and how we go deeper than other submissions will)

Most Phoenix submissions will use it as a trace viewer. We use it as the **system of record for the entire eval methodology** — and the QA agent calls it at runtime via MCP:

| Phoenix concept | How we use it | Phoenix MCP tool used |
|---|---|---|
| **Datasets** | the 50-scenario test suite is a Phoenix dataset, version-controlled and re-usable | `list-datasets`, `get-dataset-examples`, `add-dataset-examples` |
| **Experiments** | each audit run is a Phoenix experiment; head-to-head comparison across SUT prompt versions is a first-class object | `list-experiments-for-dataset`, `get-experiment-by-id` |
| **Prompts** | every judge dimension AND the SUT system prompt are versioned Phoenix prompts | `list-prompts`, `get-latest-prompt`, `upsert-prompt` |
| **Traces and sessions** | every scenario run is a full session in Phoenix; the agent reads failure spans to drive its clustering | `list-traces`, `get-spans`, `list-sessions`, `get-session` |
| **Annotations** | (stretch) reviewer feedback flows back into the dataset | `list-annotation-configs` |

That's 4 tool categories in *read mode* and 2 in *write mode*. The "write mode" use of `upsert-prompt` (rewriting the SUT) and `add-dataset-examples` (growing the test suite from real failures) is the equivalent depth play the Fivetran scaffold had with `create_connection` — and it's what the judging tiebreaker rewards.

## Stack

| Layer | Tech |
|---|---|
| Orchestration | **Google ADK** (`Agent`, `FunctionTool`, `McpToolset`) on Gemini 2.5 Pro |
| Tracing | `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)` |
| Eval platform | **Arize Phoenix Cloud** (free tier) |
| MCP | `@arizeai/phoenix-mcp@latest` mounted as an ADK toolset |
| SUT | Separate ADK agent — Gemini 2.5 Flash for speed and to keep cost down |
| Backend | FastAPI on **Cloud Run**, SSE streaming for the live thinking panel |
| Frontend | Next.js + shadcn + Tailwind; embedded Phoenix iframe in a side panel |
| Secrets | Google Secret Manager |
| License | Apache-2.0 |

## Repo layout

```
02-arize-mystery-shopper/
  README.md             this file
  architecture.md       system architecture and data flow
  demo-script.md        beat-by-beat 3-min video script
  build-plan.md         day-by-day execution plan (16 days remaining)
  SCAFFOLD-NOTES.md     what's done, what's stubbed, risks
  agent/
    README.md           Python project layout and run instructions
    pyproject.toml      dependencies (ADK + OpenInference + Phoenix)
    .env.example        environment variables
    Makefile            quickstart (make seed, make run, make loop, make deploy)
    qa_agent/           the QA agent (ADK)
      __init__.py
      main.py           CLI / FastAPI entrypoint
      instrumentation.py  Phoenix tracing setup
      agent.py          root_agent: Gemini 2.5 + tools + MCP toolset
      prompt.py         the QA agent's system instruction
      tools/
        scenarios.py    run_scenario tool
        cluster.py      cluster_failures tool
        mutate.py       mutate_sut_prompt tool
    sut/                the Subject Under Test (also ADK)
      __init__.py
      agent.py          root_agent: deliberately-flawed VelvetMint support agent
      prompt.py         the SUT's initial flawed instruction
      tools.py          mock VelvetMint domain tools (order lookup, refund, etc.)
    scenarios.py        the 10-scenario seed; the full 50 live in Phoenix
    judge_prompts.py    versioned judge prompts (6 dimensions)
  scripts/
    seed_phoenix.py     idempotent dataset + prompt seeder
    run_loop.py         single-shot self-improvement demo loop
  frontend/             Next.js dashboard (post-MVP)
  infra/
    Dockerfile
    cloud-run.yaml
```

## Quickstart

See `agent/README.md` for the long version. Short version:

```bash
cd 02-arize-mystery-shopper/agent
cp .env.example .env
# fill in PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT (must include /s/<space>),
# GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION

uv sync
make seed        # idempotent: writes 6 judge prompts + 50 scenarios into Phoenix
make run-sut MESSAGE="I want to use your 90-day price-match guarantee"
                 # smoke-test the SUT alone (single ADK turn, trace appears in Phoenix)
make run-loop    # the demo loop: baseline -> cluster -> mutate -> rerun -> delta
```

## License

Apache-2.0. See workspace `LICENSE`.
