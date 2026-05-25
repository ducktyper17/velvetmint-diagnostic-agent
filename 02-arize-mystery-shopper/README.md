# Voice-AI Mystery Shopper

> **Status:** Backup track scaffold for the Google Cloud Rapid Agent Hackathon (deadline June 11, 2026). Primary submission is on the Fivetran track (`../01-fivetran-dtc-diagnostic/`). This project exists in case we pivot in week 1.

## One-liner

**We don't audit your AI. We audit your competitors' AI.**

An autonomous agent that stress-tests other companies' AI customer-support and voice agents — runs a curated scenario suite against them, scores each conversation with an Arize Phoenix LLM-as-judge across six dimensions, and produces a competitive-intelligence report ranking the AIs head-to-head.

## The problem

Every company shipping an AI customer-support agent has the same two questions:

1. **"How does our agent compare to our competitors'?"** Today, the only way to answer this is to manually open four chat windows, type the same question, and squint. No one does it at scale.
2. **"Where do their agents fail so we can market against them?"** Sales teams pay analysts to do this manually; the work is slow, subjective, and obsolete the day it ships.

There is no commercial product in 2026 that systematically benchmarks third-party AI agents end-to-end with reproducible eval methodology.

## The user

Two buyers, same product:

- **AI product leaders** at companies shipping customer-facing agents (insurance, hospitality, airlines, telecom). They want a defensible benchmark report before their board meeting.
- **Competitive-intelligence analysts** at consultancies and VC firms who currently scrape demos by hand.

## How it works

```
User picks targets:  "Marriott, Hilton, Hyatt, IHG concierge AIs"
                          |
                          v
+----------------------------------------------------------+
| Orchestrator agent (Gemini 3 on Vertex AI)               |
|                                                          |
|  1. Pulls 50-scenario test suite from Phoenix dataset    |
|  2. For each target x each scenario:                     |
|       - drives a multi-turn conversation as the customer |
|       - logs every span/trace to Phoenix                 |
|  3. Runs Phoenix experiments: LLM-as-judge across 6 dims |
|  4. Aggregates results into a competitive report        |
+----------------------------------------------------------+
                          |
                          v
        Report:  "Marriott AI fails on Spanish-
                  accented inputs 34% of the time.
                  Hilton fails 12%. ..."
```

The six judge dimensions are: **Empathy, Accuracy, Escalation Appropriateness, Bias / Fairness, Hallucination, Brand Voice**. Each is a versioned prompt in Phoenix (`upsert-prompt`) so the eval methodology is itself auditable.

## Why Arize Phoenix is load-bearing

Most "AI evaluation" submissions will use Phoenix as a passive trace viewer. We use it as the **system of record for the entire eval methodology**:

- **Datasets** — the 50-scenario test suite is a Phoenix dataset, version-controlled and reusable across runs.
- **Experiments** — each audit run is a Phoenix experiment, so head-to-head comparisons across vendors and over time are first-class objects, not screenshots.
- **Prompts** — every judge dimension is a versioned Phoenix prompt; we can prove which rubric produced which score.
- **Traces and sessions** — every test conversation is a full session in Phoenix; reviewers can click into any single failure.

This makes the report defensible. A buyer can re-run the same experiment from the Phoenix UI without our agent in the loop.

## Stack

| Layer | Tech |
|---|---|
| Orchestration | Google Cloud Agent Builder + Gemini 3 (Vertex AI) |
| Eval platform | Arize Phoenix (Cloud or self-hosted) via `@arizeai/phoenix-mcp` and Python SDKs |
| Backend | FastAPI on Cloud Run |
| Tracing | OpenTelemetry via `arize-phoenix` Python SDK |
| Report | Server-rendered HTML, PDF export (post-MVP) |

## Repo layout

```
02-arize-mystery-shopper/
  README.md             this file
  architecture.md       system architecture and data flow
  demo-script.md        beat-by-beat 3-min video script
  SCAFFOLD-NOTES.md     what's done, what's stubbed, risks
  agent/
    README.md           Python project layout and run instructions
    pyproject.toml      dependencies
    .env.example        environment variables
    main.py             FastAPI app + /audit endpoint
    scenarios.py        test scenario data classes (10 of 50)
    judge.py            LLM-as-judge runner per dimension
    prompts.py          versioned judge prompts (6 dimensions)
```

## Quickstart

See `agent/README.md`. Short version: copy `.env.example` to `.env`, fill in the secrets, `pip install -e .`, `uvicorn main:app --reload`, POST a list of target URLs to `/audit`.

## License

To be added before submission. MIT or Apache-2.0.
