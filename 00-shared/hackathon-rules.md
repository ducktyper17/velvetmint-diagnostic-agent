# Hackathon constraints — verified from the official rules

Sources: [Official Rules](https://rapid-agent.devpost.com/rules), [Resources page](https://rapid-agent.devpost.com/resources), [Discussion forum](https://rapid-agent.devpost.com/forum_topics). Read on May 23, 2026.

This document is the canonical source of truth for what we MUST do. If something contradicts a project-level doc, this wins.

---

## 1. Eligibility — confirm BEFORE building anything

**You must NOT be a resident of**: Italy, Brazil, Quebec (CA), Crimea, Cuba, Iran, Syria, North Korea, Sudan, Belarus, Russia, Afghanistan, Antarctica, China, Djibouti, Iraq, Kazakhstan, Somalia, Venezuela, Vietnam, Western Sahara, or the Crimea/Donetsk/Luhansk regions of Ukraine.

**You must be above the age of majority** in your country of residence (or 20+ in Taiwan).

**You must have internet access as of September 16, 2025** (not an issue).

> **Action**: confirm you're not in any of the void countries. If you are, the project goes nowhere regardless of how good it is.

## 2. Critical dates

| Date | Event |
|---|---|
| May 5, 2026 (12:00 PM PT) | Contest opens (already open) |
| **June 4, 2026** | **Last day to apply for the $100 GCP credit form** (but [May 21 update](https://rapid-agent.devpost.com/resources): credits are first-come-first-served and supply is limited — apply TONIGHT) |
| **June 11, 2026 (2:00 PM PT)** | **Submission deadline — hard cutoff, no extensions** |
| June 22 – July 6, 2026 | Judging period |
| July 7, 2026 | Winners notified |

**This affects our build**: the hosted demo URL must remain accessible during the **June 22 – July 6 judging window**. See `trial-expiry-risk.md` for why this is a problem with Fivetran's 14-day trial.

## 3. What we must build (Section 7.A of rules — verbatim)

> "Build a functional agent—powered by Gemini and Google Cloud Agent Builder—that integrates a Partner Entity's MCP server to solve a real challenge."

Three hard requirements:

1. **Gemini** (we'll use Gemini 3 via Vertex AI)
2. **Google Cloud Agent Builder** — note: there's confusion in the [forum](https://rapid-agent.devpost.com/forum_topics) about the name. Several posts say it's now called "Agent Platform → Studio" in the GCP console. Same thing. We use whichever name it lives under at build time.
3. **At least one partner MCP server** — for us: Fivetran

## 4. AI USAGE LIMITATION — critical (Section 7.B, verbatim)

> "Projects are required to utilize Google Cloud artificial intelligence tools, as detailed at https://cloud.google.com/terms/services (with examples including Gemini models on Agent Platform, BigQuery ML, and relevant APIs). You may also use the built-in AI-powered features within the specific Partner's products relevant to your chosen track. **All other artificial intelligence tools are not permitted.**"

What this means for our stack:

| Layer | Allowed | NOT allowed |
|---|---|---|
| Agent reasoning | Gemini 3 (Vertex AI) | OpenAI, Anthropic Claude, Llama, Mistral |
| Embeddings | `text-embedding-005`, `gemini-embedding-001` (Vertex AI) | OpenAI `text-embedding-3`, Cohere |
| Vision / multimodal | Gemini 3 multimodal | GPT-4 Vision |
| Speech | Google Cloud Speech-to-Text, Gemini Live | Whisper, ElevenLabs |
| Code / data ML | BigQuery ML | external ML APIs |
| **Exception** | partner's built-in AI features within their own product | — |

**For our Fivetran project this is easy** — we only need Gemini 3 + Fivetran. No competing AI calls anywhere.

**For backups**:
- Arize Phoenix LLM-as-judge: judge model MUST be Gemini, not GPT-4 (Phoenix defaults to OpenAI in some examples — we override).
- MongoDB Doctor's Note: Voyage AI for embeddings is OK because MongoDB acquired Voyage in 2024 — it counts as MongoDB's "built-in AI feature." Document this clearly in the README if we pivot.

## 5. Competing-services limitation (Section 7.B, verbatim)

> "The use of other services that directly compete with Google Cloud (for cloud platform capabilities) or with the Partner whose track you've selected is not permitted."

For us:
- ✅ GCP (Vertex AI, Cloud Run, Cloud Functions, Cloud Build, Secret Manager, BigQuery)
- ❌ AWS, Azure (cloud competitors)
- ❌ Airbyte, Stitch, Meltano (Fivetran competitors)
- ✅ MongoDB Atlas (not a Fivetran competitor — it's a destination/source)
- ✅ GitHub (we can use it as the code repo; the hackathon docs reference GitLab MCP but don't require GitLab.com for the *repo*)

## 6. Submission checklist (Section 7.B)

- [ ] **Hosted Project URL** — publicly accessible (no auth wall blocking judges). Tested in incognito. Working during the June 22 – July 6 judging window.
- [ ] **Public GitHub repo** — with a **detectable open source license file** (MIT or Apache 2.0) at the root, visible in GitHub's "About" section.
- [ ] **Text description** on Devpost — summary of features, tech used, data sources, learnings.
- [ ] **Demo video ≤3 minutes** — must be on **YouTube or Vimeo only**, English or English subtitles, shows the project running. *Anything past 3:00 is ignored.*
- [ ] **Track selection** — one of {Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace}. We're picking Fivetran.
- [ ] **Devpost submission form** — all required fields complete.
- [ ] **Submit ≥48 hours before deadline** — target June 9, 2026 to leave buffer.

## 7. Multiple submissions (Section 7, "Multiple Submissions")

We CAN submit multiple times if each submission is "unique and substantially different." **A Submission can win a maximum of one prize**, but two submissions to two different tracks = two shots at the prize pool.

**Decision**: We're solo with 19 days. Default plan = one excellent Fivetran submission. If we hit our deadlines comfortably by Day 14, we can scope a quick lighter Arize backup submission for an additional shot. See `DECISION.md` for the trigger gate.

## 8. Judging criteria (Section 8, verbatim)

> Equal weighted criteria:
> - **Technological Implementation**: Does the interaction with Google Cloud and Partner services demonstrate quality software development?
> - **Design**: Is the user experience and design of the project well thought out?
> - **Potential Impact**: How big of an impact could the project have on the target communities?
> - **Quality of the Idea**: How creative and unique is the project?

Stage 1 is pass/fail on submission completeness. Stage 2 is the scored evaluation. Ties broken on the criteria above in order (Tech > Design > Impact > Idea).

Wait — note that. **Ties are broken on Tech first.** So if it comes down to us vs. another team with the same total score, the engineering quality decides it. That tilts more weight toward making the Fivetran MCP integration *deep*, not decorative.

## 9. Intellectual property (Section 12)

> "The entrant hereby licenses…the Non-Proprietary Aspects of the Submission and the source code…under an Open Source Initiative-approved license."

Translation: our repo must be OSI-licensed. **MIT or Apache 2.0** are both fine. We'll use Apache 2.0 (slightly stronger patent grant).

## 10. Upcoming partner events we should attend

From the [Resources page](https://rapid-agent.devpost.com/resources):

| Date | Event | Why |
|---|---|---|
| **Tue May 27, 12:00 PM EDT / 9:00 AM PDT** | **Fivetran + Google Cloud Q&A webinar** — [register](https://go.fivetran.com/webinars/hackathon-qa-power-your-ai-agent-with-data-fivetran-and-google-cloud) | **MANDATORY for our track.** Ask about extended trials, ask about which MCP write-mode tools are gated. |
| Mon May 26, 1:00 PM EDT | GitLab + Gemini build session, Discord | Skip — not our track. |
| Wed May 28, 1:00 PM EDT | Phoenix MCP build session, Discord | Skip — backup track. |

## 11. Known issues from the forum (things to watch for)

From [forum topics](https://rapid-agent.devpost.com/forum_topics):

- *"Cannot find 'Google Cloud Agent Builder'"* — it lives under **Agent Platform → Studio** in the current GCP console UI. Same product.
- *"Unable to redeem Gemini credits coupon - billing accounts flagged as inactive"* — common. Solution: make sure the billing account is fully activated (need a payment method on file even for free trial, or it gets flagged inactive).
- *"What if I don't have Gemini Enterprise?"* — Gemini Enterprise (paid tier) vs Gemini API (free trial) — the hackathon is fine with the free-trial path. Just use Vertex AI SDK.
- *"Antigravity instead of Agent Builder"* — Antigravity is Google's new agentic IDE (2026). The rules require Agent Builder, not Antigravity, so we stick with Agent Builder.
- *"Should GitLab track must use MCP server?"* — yes, per Section 7.A all tracks require the partner MCP. Not optional.

## 12. Mistakes that disqualify

- Submitting late (after 2:00 PM PT June 11)
- Repo not public, or missing OSI license file at root
- Demo video on Loom/Drive instead of YouTube/Vimeo
- Using AI tools that aren't Google (e.g., calling Anthropic's API from our agent)
- Using cloud services that compete with GCP (e.g., agent hosted on AWS Lambda)
- Hosted URL behind auth wall when judges visit
- Submission isn't substantially different from existing work (we're building from scratch — we're fine)
