# Google Cloud Rapid Agent Hackathon — Workspace

**Deadline:** June 11, 2026 (Thu, 2:00 PM PDT) — hard cutoff
**Judging:** June 22 – July 6, 2026 (our hosted demo URL must stay up during this window)
**Prize per track:** $5K / $3K / $2K
**Total tracks:** 6 — Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace

**Hard requirements** (from the [official rules](https://rapid-agent.devpost.com/rules)):
1. Functional agent **powered by Gemini and Google Cloud Agent Builder**
2. Integrates one **partner MCP server** (Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace)
3. **No non-Google AI tools allowed** (no Claude, no OpenAI, no Cohere) — only Gemini + partner-built-in AI features
4. Hosted URL + public OSI-licensed repo + ≤3-min YouTube/Vimeo demo video

See `00-shared/hackathon-rules.md` for the full canonical rules with citations.

## Strategy

We're building **one excellent agent**, not six mediocre ones. This workspace contains:

- **Deep scaffold** of the top pick we'll actually build.
- **Mid-depth scaffold** of two backups in case we pivot in week 1.
- **One-pagers** for the other three tracks so we have full optionality.

## Top pick

**Fivetran track — DTC Brand Health Diagnostic Agent.**

An owner of a small DTC e-commerce brand asks: *"Why is my revenue down 22% this month?"* The agent autonomously sets up Fivetran connectors to Shopify, Klaviyo, Meta Ads, Google Ads, TikTok Ads, Stripe, and the brand's review platform. It syncs the data, runs hybrid analytics, and produces a root-cause diagnosis: *"TikTok ROAS dropped 41% because creative is stale. Email open rate dropped 18% because list decayed (popup broken May 3). Cart abandonment up 22% because checkout JS errors on iOS Safari started May 8."*

**Why this:**

1. Uses Fivetran's MCP at the **autonomous connector-creation level** — the killer demo move where the agent wires up 6 data pipelines on the fly.
2. Fivetran is among the **least crowded tracks** because most hackathoners don't know what Fivetran is.
3. Multi-source root-cause analysis is **impossible without unified data** — Fivetran is genuinely load-bearing, not decorative.
4. Demo has a sharp **"wait, what?" moment** — agent diagnoses a real business across 6 platforms in 90 seconds.

See `DECISION.md` for the full A/B/C ranking with judge grades.

## Folder map

| Folder | Status | Idea |
|---|---|---|
| `01-fivetran-dtc-diagnostic/` | **Deep scaffold** | DTC brand health root-cause agent |
| `02-arize-mystery-shopper/` | Mid scaffold | Eval-as-a-service: test competitor AIs |
| `03-mongodb-doctors-note/` | Mid scaffold | Hybrid retrieval: decode medical reports |
| `04-elastic-apartment-detective/` | One-pager | Real-estate truth seeker |
| `05-gitlab-onboarding-agent/` | One-pager | New-hire onboarding orchestrator |
| `06-dynatrace-ai-cost-forecaster/` | One-pager | LLM-bill forecasting & changepoints |
| `00-shared/` | — | MCP cheatsheets, GCP stack, hackathon rules, judging rubric, trial-expiry mitigation |
| `synthetic-data/` | ✅ Done | Story-driven fake DTC dataset (Shopify/Klaviyo/TikTok/Meta/Google/Stripe/Yotpo) |

## What you need to do today

See `SETUP.md` — the gating items (GCP $100 credit form, partner trial signups) take 1–5 days to approve. **Apply tonight.**

## Build timeline (19 days)

- **Days 1–2** (May 24–25): Setup. Apply for credits, create accounts, get Agent Builder + Gemini 3 access.
- **Day 4 (Tue May 27, 12 PM EDT)**: Attend the [Fivetran + Google Cloud webinar](https://go.fivetran.com/webinars/hackathon-qa-power-your-ai-agent-with-data-fivetran-and-google-cloud) — ask about extended trials.
- **Days 3–7**: Build the agent end-to-end with **hardcoded fake data**. Prove the full loop works.
- **Days 8–13**: Replace mocks with real MCP integrations, polish the dashboard, **record 5–10 reference agent traces** to MongoDB before the Fivetran trial expires (~June 7).
- **Days 14–17**: Switch the hosted demo to DEMO mode (cached replay), polish, record the 3-min video, write the Devpost narrative.
- **Days 18–19**: Buffer + submit ≥48 hours before deadline.

Detailed day-by-day in `01-fivetran-dtc-diagnostic/build-plan.md`. Trial-expiry plan in `00-shared/trial-expiry-risk.md`.
