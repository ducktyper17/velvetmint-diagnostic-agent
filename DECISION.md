# DECISION — Why the MongoDB path is active now

## The judging rubric

Per [the hackathon page](https://rapid-agent.devpost.com/), the score is driven by:

1. **Technological Implementation**
2. **Design**
3. **Potential Impact**
4. **Quality of the Idea**

The fourth criterion is still the one most teams will underweight. We do not
just need a working agent; we need one whose partner integration feels
essential and memorable in under 3 minutes.

## Updated ranking — execution reality included

| Rank | Idea | Track | Grade | Comment |
|---|---|---|---|---|
| **1** | **Doctor's Note Decoder** | **MongoDB** | **A** | Best balance of strong emotional demo, obvious Atlas fit, and realistic build speed from where the repo is today. |
| 2 | DTC Brand Health Diagnostic | Fivetran | A | Great concept, but heavier partner, trial, and sandbox risk with more moving parts to stabilize quickly. |
| 3 | Voice-AI Mystery Shopper | Arize | A | High novelty, but weaker instant emotional hook than the MongoDB path. |
| 4 | Apartment Hunting Detective | Elastic | A | Strong user value, but data-ingest work still dominates the schedule. |
| 5 | Engineering Onboarding Agent | GitLab | A- | Solid product idea, crowded track. |
| 6 | Production AI Cost Forecaster | Dynatrace | A | Interesting, but the story is less immediate for judges. |

## Why MongoDB wins from here

### 1. Atlas is genuinely load-bearing

The core user-facing magic is a MongoDB problem:

- one Atlas knowledge base
- multiple collection shapes
- one aggregation pipeline with vector search plus structured filters
- saved user history in the same database

That is far stronger than "we used MongoDB somewhere in the stack."

### 2. The demo is immediate

Judges do not need domain setup to understand it:

- confusing report goes in
- structured retrieval happens live
- plain-language explanation comes out

That before/after is crisp, emotional, and easy to score quickly.

### 3. It is a better execution bet right now

Compared with the Fivetran concept, this path removes:

- trial-expiry pressure
- multi-SaaS sandbox setup
- connector provisioning uncertainty
- a large dashboard and pipeline surface area before the core agent works

The MongoDB project still has real work, but it is concentrated in a smaller
set of components.

### 4. The official hackathon resources map cleanly onto it

- **Agent Builder / Agent Runtime** for orchestration
- **MongoDB MCP server** for the partner action layer
- **Cloud Run** for the hosted backend
- **Secret Manager** for secrets
- **Gemini safety settings** for guardrails

That gives us a submission that looks intentional rather than stitched together.

## Non-negotiables for rules compliance

Per the [rules](https://rapid-agent.devpost.com/rules), we cannot use outside AI
providers. That means:

- no OpenAI
- no Anthropic
- no Cohere
- no Voyage AI embeddings

The MongoDB path therefore uses **Gemini + Vertex AI text embeddings** on the
Google side, and **MongoDB Atlas + the official MongoDB MCP server** on the
partner side.

## Guardrails for the MongoDB path

We only pursue this path if all three remain true:

- [ ] The agent never presents itself as diagnosing the patient.
- [ ] The demo stays scoped to report explanation, cited context, and follow-up questions.
- [ ] The Atlas retrieval step is visible enough in the video that judges can see why MongoDB matters.

If the legal framing starts to wobble, we narrow scope further to radiology
report explanation only instead of broad "medical report understanding."

## What we are not doing

- We are not forcing MongoDB into the Fivetran story as side storage.
- We are not using third-party embeddings that could violate the rules.
- We are not expanding to a full patient portal product for the hackathon.
- We are not broadening beyond the narrowest demoable slice before the core loop works.

## Secondary option

If the MongoDB demo becomes unsafe or unstable, the fallback is still
`01-fivetran-dtc-diagnostic/`. It remains a strong idea, just not the fastest
path to a polished, rules-safe submission from today's position.
# DECISION — Why we're building the Arize Self-Improving QA Agent

> **Updated May 26, 2026.** Switched primary submission from Fivetran DTC Diagnostic to **Arize Self-Improving QA Agent** after re-reading the [Arize partner page](https://rapid-agent.devpost.com/details/arize-resources). The partner explicitly stated the winning criteria and our Fivetran plan doesn't hit them; our Arize scaffold can. The Fivetran scaffold is preserved as a stretch second submission (rules allow it). See the "What changed" section at the bottom for the full rationale.

## The four-criterion judging rubric

Per [the hackathon page](https://rapid-agent.devpost.com/):

1. **Technological Implementation** — does the GCP + partner integration demonstrate quality engineering? **(tiebreaker first)**
2. **Design** — is the user experience well thought out?
3. **Potential Impact** — how big of an impact on the target community?
4. **Quality of the Idea** — how creative and unique?

Tiebreaker order is Tech → Design → Impact → Idea (per `00-shared/hackathon-rules.md` §8). That puts disproportionate weight on engineering depth.

## The Arize partner's own stated criteria (verbatim)

From [arize-resources](https://rapid-agent.devpost.com/details/arize-resources):

> "We'll evaluate submissions based on technical implementation, **meaningful use of tracing and MCP**, **quality of the agent's self-improvement loop**, and overall impact... **Bonus points for agents that use their own observability data to improve over time.**"

This is the most explicit signal any partner gave us about how they will score the track. Whoever builds the strongest *self-improvement loop* on top of Phoenix wins.

## Full ranking — judge hat on (post-update)

| Rank | Idea | Track | Grade | Track competition (est.) | Comment |
|---|---|---|---|---|---|
| **1** | **Self-Improving QA Agent** | **Arize** | **A+** | Low (≈100–200) | Promoted. Hits Arize's stated bonus criterion directly. No trial-expiry risk. |
| 2 | DTC Brand Health Diagnostic | Fivetran | A | Low (≈100–150) | Demoted to backup / stretch second submission. Trial-expiry risk; demo-mode disclosure overhead. |
| 3 | Doctor's Note Decoder | MongoDB | A | Medium (≈300–500) | Atlas fits hybrid retrieval. Medical liability framing risk. |
| 4 | Apartment Hunting Detective | Elastic | A | Medium (≈200–400) | Heavy data-ingest work. |
| 5 | Engineering Onboarding Agent | GitLab | A− | High (≈500+) | Crowded track is the real obstacle. |
| 6 | Production AI Cost Forecaster | Dynatrace | A | Low–medium | Forecasting+changepoints used in fresh way. |

## Why Arize Self-Improving QA Agent wins

### 1. Tech Implementation — A+ (this is the tiebreaker)

The Phoenix MCP server is genuinely load-bearing in **both directions**:

- **Read side**: agent calls `list-traces`, `get-spans`, `list-experiments-for-dataset`, `get-experiment-by-id` at runtime to read its OWN failure spans — this is the literal definition of "introspect at runtime" from the partner page.
- **Write side**: agent calls `upsert-prompt`, `add-dataset-examples`, and writes experiment rows to mutate the eval methodology and grow the test suite without a code deploy.

That's the equivalent of "write-mode connector creation" but for evals — same engineering-depth play that made the original Fivetran pick strong. Stack: Google ADK (`Agent` + `FunctionTool` + `McpToolset`) + `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)` + Cloud Run. Canonical, matches the [Arize gemini-hackathon reference repo](https://github.com/Arize-ai/gemini-hackathon).

### 2. Quality of Idea — A+

No shipped product does "agent that audits another Gemini agent, finds failure clusters, rewrites the SUT's system prompt, re-runs the eval, and proves a score delta — all with Phoenix as the system of record" in 2026. The closest analogs (Patronus, Braintrust, Promptfoo, Humanloop) are human-driven dashboards. We make the agent the QA engineer.

### 3. Design — A

ADK streams `events()` we render as a live "thinking" panel. Phoenix UI is embedded in a side panel so reviewers can click into any session, prompt version, or experiment row themselves. Final report is a versioned diff: "system prompt v1 → v2", "hallucination 23% → 6%", side-by-side judge rationales on a representative failing scenario.

### 4. Impact — A

Every team shipping a Gemini agent (millions of teams by 2026) has this exact pain. "Eval as code gate" is a real CI/CD product wedge. The demo's claim — "an AI quality engineer that never sleeps" — is one any AI product leader has fantasized about.

## Why we deprioritized the Fivetran build (preserving it as backup)

- **Trial expiry**: 14-day Fivetran trial expires ~June 7, before the June 22 judging window. We had a "demo mode replay" plan in `00-shared/trial-expiry-risk.md` but it added complexity and risked judges scoring us as "not actually live" in Stage 1 completeness.
- **No partner-stated winning criterion**: Fivetran told us about tools, not about how they would score. Arize told us exactly.
- **Crowding parity**: both tracks are low-competition (~100–200 estimated), so we don't gain meaningful crowd-cover by sticking with Fivetran.
- **Reuses existing assets**: the `synthetic-data/` DTC corpus we already built is reused as the SUT's context (the SUT is a customer-support agent for the fake brand). Zero waste.

The Fivetran scaffold and the synthetic-data work stay in the repo. **If we hit our Arize deadlines comfortably by Day 14 (June 6)**, we ship the Fivetran scaffold as a second submission (rules Section 7 allows it; single submission can win one prize but two submissions = two shots at the pool).

## When to pivot again (decision gate: Day 4 / May 30)

We pivot only if any of these break on Day 4:

- [ ] **Phoenix Cloud account / API key blocked.** (Fallback: self-hosted Phoenix in Docker — supported officially, no functional loss.)
- [ ] **ADK + Phoenix MCP integration spike fails.** (Fallback: drop ADK and use Vertex AI SDK directly with `openinference-instrumentation-vertexai` — same Phoenix tracing, less elegant tool surface.)
- [ ] **Cannot make Gemini 2.5 reliably mutate its own prompt with measurable improvement.** (Fallback: scope down — present the analysis without the prompt-rewrite step. Still hits the "uses its own observability data" criterion, just less dramatic.)

## Critical constraint we just learned (Section 7.B)

Per the [rules](https://rapid-agent.devpost.com/rules): *"All other artificial intelligence tools are not permitted."* Means we cannot call Anthropic, OpenAI, or any non-Google AI from our agent. Specifically for Arize: the LLM-as-judge MUST be Gemini, not GPT-4 (Phoenix defaults to OpenAI in some examples — we override). The SUT must also be Gemini. Captured in `00-shared/hackathon-rules.md`.

## What changed (May 26 update changelog)

| Item | Before | After |
|---|---|---|
| Primary track | Fivetran | **Arize** |
| Arize concept | "Voice-AI Mystery Shopper" — audit competitor AIs | **"Self-Improving QA Agent"** — audit a reference Gemini agent and rewrite its prompts to fix regressions |
| Phoenix MCP role | Python `mcp` client; control plane only | **`McpToolset` inside ADK** — agent uses MCP as runtime tools; read+write |
| Agent runtime | FastAPI + `google-cloud-aiplatform` SDK | **Google ADK** (`Agent` + `FunctionTool` + `McpToolset`) |
| Tracing | manual OTel TODO | `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)` (auto-instrumented) |
| Subject under test | live competitor chatbots (TOS + rate-limit risk) | a deliberately-flawed Gemini support agent we control (no risk, deterministic demo) |
| Trial expiry | demo-mode replay needed (June 7 cliff) | none — Phoenix Cloud free tier is permanent |
| Fivetran scaffold | primary submission | preserved as backup + optional stretch second submission |
