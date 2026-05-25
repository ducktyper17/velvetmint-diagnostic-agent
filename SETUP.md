# SETUP — Do these TODAY (May 23)

Several items have approval delays AND the [May 21 update on the resources page](https://rapid-agent.devpost.com/resources) says GCP credits are now **first-come-first-served while supplies last**. Apply tonight or we lose them.

## 0. Eligibility check (30 seconds — do first)

The [official rules](https://rapid-agent.devpost.com/rules) (Section 4) make the contest **void** in: Italy, Brazil, Quebec (Canada), Crimea, Cuba, Iran, Syria, North Korea, Sudan, Belarus, Russia, Afghanistan, Antarctica, China, Djibouti, Iraq, Kazakhstan, Somalia, Venezuela, Vietnam, Western Sahara, and the Donetsk/Luhansk regions of Ukraine.

- [ ] Confirm your country of residence is NOT in that list.
- [ ] Confirm you are above the age of majority in your country (or 20+ in Taiwan).

If either fails, stop — we shouldn't sink 19 days into something that can't be submitted.

## 1. Gating accounts (do tonight — credits are running out)

- [ ] **Apply for $100 GCP credit** (deadline June 4, but apply NOW): https://forms.gle/xfv9vQzfRfNCCVbG7
  - Approval window: 1–5 business days. The [May 21 update](https://rapid-agent.devpost.com/resources) limits credits to first-come-first-served. **DO THIS FIRST.**
- [ ] **Sign up for GCP free trial** ($300, 90 days): https://cloud.google.com/free
  - Bridges the gap while waiting for the $100 credit. Add a payment method even though you won't be charged — the [forum](https://rapid-agent.devpost.com/forum_topics) shows users getting their billing accounts "flagged as inactive" when there's no payment method, and that blocks Gemini coupon redemption later.
- [ ] **Join the hackathon Discord**: https://discord.gg/7Dqk5ebCD4
  - For partner-specific Q&A. Active during build sessions.
- [ ] **Register on Devpost**: https://rapid-agent.devpost.com/
  - Click "Join hackathon" to claim your spot.

## 2. Register for the partner events (this week)

The [Resources page](https://rapid-agent.devpost.com/resources) lists these. We attend only the one relevant to our track.

- [ ] **Tue May 27, 12:00 PM EDT / 9:00 AM PDT — Fivetran + Google Cloud webinar.** [Register here](https://go.fivetran.com/webinars/hackathon-qa-power-your-ai-agent-with-data-fivetran-and-google-cloud). **Mandatory** — we have specific questions about extended trials and MCP write-mode gating (see `00-shared/trial-expiry-risk.md`).
- (Skip the GitLab session May 26 and Phoenix session May 28 — not our track.)

## 3. Google Cloud setup (Day 1, after trial activated)

- [ ] Create a new GCP project (suggested: `rapid-agent-hack-2026`)
- [ ] Confirm billing account is active (avoid the "inactive" flag from the forum)
- [ ] Enable these APIs:
  - Vertex AI API
  - Cloud Run Admin API
  - Cloud Functions API
  - Secret Manager API
  - Cloud Build API
  - BigQuery API
- [ ] Install `gcloud` CLI, authenticate, set the project as default
- [ ] Get access to **Agent Builder** — note: in the current GCP console UI, [the forum](https://rapid-agent.devpost.com/forum_topics) says it appears under **Agent Platform → Studio**. Same product.
- [ ] Verify **Gemini 3** model access (Vertex AI → Model Garden)

## 4. Partner accounts (Day 1)

Required for Fivetran DTC Diagnostic (our top pick):

- [ ] **Fivetran free trial** (14 days): https://fivetran.com/signup
  - All connectors available during the trial. **Don't activate until Day 1 of build** — see `00-shared/trial-expiry-risk.md` for why timing matters. We want it active during build days 1–14 and recording days.
- [ ] **MongoDB Atlas M0** (free forever): https://www.mongodb.com/cloud/atlas/register
  - For storing the recorded agent traces and unified data.
- [ ] **GitHub repo** — public, with an Apache 2.0 license file at the root. Required by the rules (Section 7 — repo must be public and OSI-licensed).

Demo SaaS sandbox accounts (only needed if we use real APIs instead of our generated synthetic data — most likely we use the synthetic dataset we already built):

- [ ] *Optional:* Shopify Partner + dev store: https://partners.shopify.com/signup
- [ ] *Optional:* Klaviyo free: https://www.klaviyo.com/signup
- [ ] *Optional:* Stripe test mode: https://dashboard.stripe.com/register

> **You do NOT need to spend any money.** Free/sandbox tiers cover everything.

## 5. If we pivot to a backup (decision Day 4)

**Arize backup** requires only:
- [ ] Arize Phoenix Cloud free account: https://app.phoenix.arize.com/
- Note: Phoenix's LLM-as-judge defaults to OpenAI in some examples. The [rules (Section 7.B)](https://rapid-agent.devpost.com/rules) BAN non-Google AI. We override to Gemini.

**MongoDB Doctor's Note backup** requires:
- [ ] MongoDB Atlas (already in main list)
- [ ] Voyage AI API key — this is OK to use because MongoDB acquired Voyage in 2024 and it's now a "built-in AI feature" of MongoDB (the rules permit partner-built-in AI).

## 6. Decisions needed from you

1. ✅ **Project**: Fivetran DTC Diagnostic (locked).
2. ✅ **Team**: solo (you + me).
3. **Hosting region**: `us-central1` recommended (Agent Builder + Cloud Run cheaper there).
4. **GitHub username**: tell me yours so I can scaffold the right repo URL in docs.
5. **Domain name**: optional. Cloud Run's `*.run.app` URL is fine for judging.

## 7. Critical dates (from the rules)

| Date | What |
|---|---|
| **Now** | Apply for GCP credit (first-come-first-served per [May 21 update](https://rapid-agent.devpost.com/resources)) |
| **Tue May 27, 12 PM EDT** | Fivetran + Google Cloud webinar (you attend) |
| **June 4** | Last day to submit the GCP credit form (don't wait this long) |
| **June 9** (our internal target) | Submit on Devpost — 48hr buffer before deadline |
| **June 11, 2:00 PM PT** | Official submission deadline — hard cutoff |
| **June 22 – July 6** | Judging period — hosted demo URL must work during this window |
| **July 7** | Winners notified |

## 8. What I can do vs what's blocked on you

| Task | I can do | You must do |
|---|---|---|
| Scaffold code, docs, architecture, synthetic data | ✅ | |
| Create GCP project, get credits, billing | | ✅ |
| Generate API keys (Fivetran, MongoDB, etc.) | | ✅ |
| Run/test agent end-to-end | | We both, once keys exist |
| Record the demo video | | ✅ (your voice/face) |
| Cloud Run deploys | We both | You provide auth |

## 9. Ping me when you've done

1. ✅ Submitted the GCP $100 credit form (paste a screenshot or confirmation)
2. ✅ Activated the GCP free trial (give me the project ID)
3. ✅ Registered for the Fivetran webinar (May 27)
4. ✅ Created the GitHub repo (give me the URL)

I'll keep scaffolding in parallel. The thing I CAN'T do without your project ID is start wiring real Gemini calls.
