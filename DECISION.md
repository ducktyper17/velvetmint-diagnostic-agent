# DECISION — Why we're building the Fivetran DTC Brand Health Diagnostic

## The four-criterion judging rubric

Per [the hackathon page](https://rapid-agent.devpost.com/):

1. **Technological Implementation** — does the GCP + partner integration demonstrate quality engineering?
2. **Design** — is the user experience and design well thought out?
3. **Potential Impact** — how big of an impact on the target community?
4. **Quality of the Idea** — how creative and unique?

The criterion most teams underweight is **#4 (Quality of the Idea)**. That's where we'll win or lose.

## Full ranking — judge hat on

| Rank | Idea | Track | Grade | Track competition (est.) | Comment |
|---|---|---|---|---|---|
| **1** | **DTC Brand Health Diagnostic** | **Fivetran** | **A** | Low (≈100–150) | Top pick. Fivetran's superpower is genuinely load-bearing. |
| 2 | Voice-AI Mystery Shopper | Arize | A | Low (≈100–200) | Highest novelty. Slower demo. Solid backup. |
| 3 | Doctor's Note Decoder | MongoDB | A | Medium (≈300–500) | Hybrid retrieval perfectly fits Atlas. Health liability framing risk. |
| 4 | Apartment Hunting Detective | Elastic | A | Medium (≈200–400) | Universal pain. Heavy data-ingest work. |
| 5 | Engineering Onboarding Agent | GitLab | A− | High (≈500+) | Crowded track is the real obstacle, not the idea. |
| 6 | Production AI Cost Forecaster | Dynatrace | A | Low–medium | Forecasting+changepoints used in fresh way. |

(Estimated competition based on partner brand awareness among hackathon participants and pre-existing community size; not from the closed gallery.)

## Why Fivetran DTC Diagnostic wins

### 1. Quality of Idea — A
Multi-source root-cause analysis is genuinely impossible without unified data. The agent autonomously sets up data pipelines and reasons across them. No shipped product does the full "diagnose my DTC brand across 6 platforms in 90 seconds" loop in 2026. Existing "DTC analytics" tools (Daasity, Polar Analytics, Triple Whale) are dashboards, not agents — humans still do the reasoning.

### 2. Tech Implementation — A
The Fivetran MCP is used at the **write-mode connector-creation level** (`create_connection`, `sync_connection`, `get_connection_state`, `modify_connection_schema_config`). This is exactly what the hackathon brief asks for: *"agent should plan steps and use tools to finish the job."* Most Fivetran submissions will use read-only tools; we'll use write mode. That's the differentiator.

### 3. Design — A
Conversational SMB-facing agent (text or voice). Streaming reasoning visible in a clean Next.js dashboard. The diagnosis output is structured (problem → root cause → revenue impact → fix recommendation) — easy to read in a 3-minute demo.

### 4. Impact — A
The DTC market is ~$300B globally. Every brand owner has had this exact panic moment. The target user (DTC founder/operator) is sympathetic and the dollar amounts in the demo are concrete.

## When to pivot (decision gate: Day 4 / May 27)

We pivot to a backup IF any of these are true on Day 4:

- [ ] **GCP Agent Builder access blocked.** (Fallback: use Vertex AI directly — same model, more work.)
- [ ] **Fivetran free trial is restrictive enough to break the demo.** (Fallback: pivot to Arize Mystery Shopper which has no partner-data dependency.)
- [ ] **Can't get 3+ partner SaaS sandboxes working.** (Fallback: pivot to MongoDB Doctor's Note which only needs Atlas + Voyage.)

## Why we are NOT building each alternative (the case for committing)

- **Mystery Shopper (Arize)**: Slower demo. Score reports are less viscerally dramatic than "agent fixed my business." A− potential ceiling.
- **Doctor's Note (MongoDB)**: Medical liability requires careful framing in 19 days. Also MongoDB track is more crowded.
- **Apartment Detective (Elastic)**: Data ingestion (HPD violations, Reddit, Yelp, etc.) is the bulk of the work. Less time on the agent itself.
- **Onboarding (GitLab)**: Most crowded track. Even an excellent submission may be top-15 not top-3.
- **AI Cost Forecaster (Dynatrace)**: Simulating LLM cost telemetry into Dynatrace is tedious. Strong idea, harder build.

## What changes our mind

A single A+ insight nobody's mentioned — bring it. The Devpost gallery isn't public yet, so we won't know what's been submitted until after we submit. We bet on the strongest hand we can play.

## Stretch: a second submission for a second prize pool

The [official rules](https://rapid-agent.devpost.com/rules) (Section 7, "Multiple Submissions") allow an entrant to submit multiple substantially different projects. A single submission can win only one prize, but two submissions to two different tracks = two independent shots at the prize pool.

**Gate**: if by **Day 14 (June 6)** our Fivetran submission is complete and the recorded traces (see `00-shared/trial-expiry-risk.md`) are in place, we have 5 spare days. We use them to ship a stripped-down Arize Mystery Shopper as a second submission. Not a polished demo, but enough to clear Stage 1 (pass/fail viability) and get a real Stage 2 score on the Arize track.

If the Fivetran build is still wobbling on Day 14, we skip the second submission and finish polishing the primary. We don't sacrifice the strong submission for a weaker second one.

## Critical constraint we just learned

Per the [rules (Section 7.B)](https://rapid-agent.devpost.com/rules): *"All other artificial intelligence tools are not permitted"* — meaning we cannot call Anthropic, OpenAI, Cohere, or any non-Google AI from our agent. Only Gemini and partner-built-in AI features. This is fine for Fivetran (we only need Gemini). It matters for the Arize backup (LLM-as-judge must be Gemini, not GPT-4) and is captured in `00-shared/hackathon-rules.md`.
