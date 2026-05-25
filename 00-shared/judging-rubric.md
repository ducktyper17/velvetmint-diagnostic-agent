# Self-Scoring Rubric

We will score our own submission against this rubric weekly, brutally. Target: 9+/10 on all four criteria by Day 17.

## Criterion 1: Technological Implementation

Question: Does the interaction with GCP + the partner MCP demonstrate quality software development?

| Score | Description |
|---|---|
| 10 | Production-quality code, the partner MCP is genuinely load-bearing (not decorative), multi-step agent loop is robust, proper error handling, deployment is clean. |
| 8 | Solid code, the MCP is doing real work, agent loop works but has rough edges. |
| 6 | Code works for the happy path. MCP is used but partially decorative. |
| 4 | Demo-level code. MCP is just "I called one tool." |
| 2 | Mostly mock. |

**Where we win**: Fivetran in WRITE mode autonomously creating connectors. That's an A+ technical move.

## Criterion 2: Design (UX)

Question: Is the user experience well thought out?

| Score | Description |
|---|---|
| 10 | Beautiful, intuitive, looks like a real product. Loading/streaming states are polished. Error states handled. Mobile-friendly. |
| 8 | Clean, looks professional, may have a few rough edges. |
| 6 | Functional, not pretty. |
| 4 | Engineer-aesthetic, raw API responses visible. |
| 2 | Terminal output only. |

**Where we win**: Next.js + shadcn + Tailwind + SSE streaming of agent reasoning. The visible "agent thinking" is the design moment.

## Criterion 3: Potential Impact

Question: How big of an impact could this have on the target community?

| Score | Description |
|---|---|
| 10 | Universal pain, huge market, agent meaningfully better than alternatives, would be venture-fundable. |
| 8 | Real pain, large market, clear differentiation. |
| 6 | Pain is real but niche; or market is large but differentiation is unclear. |
| 4 | Pain is theoretical, market is small. |
| 2 | Vanity product. |

**Where we win**: DTC e-commerce is a $300B market. Every DTC founder has had this exact panic moment. We're delivering on a real, named pain.

## Criterion 4: Quality of the Idea

Question: How creative and unique is the project?

| Score | Description |
|---|---|
| 10 | "I haven't seen anything like this. Why doesn't this exist?" |
| 8 | Fresh angle on a known problem. |
| 6 | Solid execution of an idea I've seen before. |
| 4 | Variation on a popular hackathon trope. |
| 2 | Yet another postmortem/CVE/log-analysis agent. |

**Where we win**: No shipped product does the full "diagnose my DTC brand across 6 platforms in 90 seconds" loop with autonomous connector creation. The closest analogue (Triple Whale, Polar Analytics, Daasity) is a dashboard, not an agent.

## Weekly self-score targets

| Date | Tech | Design | Impact | Idea | Total |
|---|---|---|---|---|---|
| Day 7 (May 30) | 6 | 4 | 8 | 9 | 27/40 |
| Day 14 (June 6) | 8 | 7 | 8 | 9 | 32/40 |
| Day 17 (June 9) | 9 | 9 | 9 | 9 | 36/40 |
| Day 19 (June 11, submit) | 9+ | 9+ | 9 | 9+ | 36+/40 |

Below 8 on any criterion by Day 17 = trigger pivot or scope cut.

## Honest pre-mortem (what could kill us)

- **Fivetran feels decorative** → mitigate by going deep on `create_connection` + `modify_connection_schema_config` in WRITE mode
- **Mock data feels mock** → mitigate by using real sandbox accounts (Shopify dev store, Stripe test mode, Klaviyo free) with real test data
- **Agent feels like a dashboard** → mitigate by hard-coding multi-step reasoning visible to the user (the "thinking" stream is the demo moment)
- **Demo video is boring** → mitigate by writing the script before the build, recording at 95% polish on Day 17, leaving Day 18 for re-record
- **Voice-AI Mystery Shopper (backup) gets sniped by a competitor** → it's a backup, we won't lose much
