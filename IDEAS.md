# Google Cloud Rapid Agent Hackathon — Project Ideas

**Deadline:** June 11, 2026
**Prize:** $5,000 (1st) / $3,000 (2nd) / $2,000 (3rd) per partner track — $10,000 per track pool
**Required stack:** Google Cloud Agent Builder + Gemini 3 + at least one partner MCP server

---

## Idea 1: Autopsy Agent

> When production breaks, an agent autonomously writes a complete postmortem in 5 minutes instead of 5 hours.

### The problem & user

- **Who:** On-call engineers, engineering managers, anyone post-incident
- **Pain:** Postmortems take 4–8 hours to write, happen days late, and are often shallow because by then nobody remembers the details. Every company has bad postmortem culture.
- **Why now:** Incident frequency keeps rising. SOC2 / customer SLAs increasingly require formal RCA docs. This is a tax every engineering org pays.

### What the agent does

1. Detects "incident resolved" signal from Dynatrace
2. Pulls full incident timeline (when started, services affected, error patterns, recovery point)
3. Pulls recent deployments and commits from GitLab around the incident window
4. Cross-references error stack traces with code paths in suspect commits
5. Queries past similar incidents in MongoDB for context
6. Quantifies impact (affected requests, error counts, duration)
7. Generates a full postmortem document: summary, timeline, root cause, impact, action items
8. Posts to MongoDB (incident knowledge base) + opens draft PR in GitLab with `postmortems/2026-05-14-checkout-outage.md`

### Demo flow (3-min video, beat by beat)

| Time | Beat |
|---|---|
| 0:00–0:15 | **Hook:** "The average postmortem takes 4–8 hours. By the time it's written, half the team has forgotten the details." |
| 0:15–0:30 | Staged outage: checkout error rate spikes in Dynatrace dashboard |
| 0:30–0:45 | Mock engineer hotfixes; errors normalize; "incident resolved" banner |
| 0:45–1:00 | Agent wakes up. Dashboard activates. |
| 1:00–2:30 | **Live reasoning visible:** "Pulling Dynatrace events 14:32–15:07..." → "Identifying affected services..." → "Pulling commits in window..." → "Cross-referencing stack traces with diffs..." → "Querying past incidents..." → "Drafting document..." |
| 2:30–2:45 | Postmortem document materializes section by section — exec summary, timeline w/ timestamps, root cause, impact, action items |
| 2:45–3:00 | Cut to GitLab — draft PR exists with the markdown file. Tagline + tech stack. |

### Architecture

```
Dynatrace "incident closed" event → Cloud Function webhook → Agent
                                                              ↓
                  Agent Builder + Gemini 3 orchestrates MCP tools:
                  ┌─────────────┬───────────────┬──────────────┐
                  ↓             ↓               ↓              ↓
              Dynatrace      GitLab         MongoDB       (later: Arize
              (timeline,    (commits,      (past             for postmortem
               traces,       diffs,         incidents,        quality eval)
               services)     deploys)       runbooks)
                                                              ↓
                            Postmortem.md → MongoDB + GitLab draft PR
                                                              ↓
                            Live dashboard streams reasoning to UI
```

### Partner roles & submission track

| Partner | Role |
|---|---|
| **Dynatrace** ⭐ | Incident detection, timeline, impact data — *submission track* |
| GitLab | Code + commits + creating the PR |
| MongoDB | Incident knowledge base + storage |
| Arize (optional) | Evaluating postmortem quality |

**Why Dynatrace track:** lower competition than GitLab/Mongo, and the story genuinely centers on observability data.

### Tech stack

- **Agent:** Google Cloud Agent Builder + Gemini 3 (Python SDK, not low-code — better for judges)
- **Broken demo app:** Node.js/Express e-commerce checkout on Cloud Run
- **Traffic generator:** simple Node script hitting the API to produce realistic telemetry
- **Frontend dashboard:** Next.js + shadcn + Tailwind on Cloud Run, SSE for live agent reasoning
- **Webhook glue:** Cloud Function
- **Knowledge base:** MongoDB Atlas free tier
- **Repo:** Public GitHub (mirrors a GitLab project for the partner story)

### 3-week build plan

**Week 1 — Prove it works**
- D1: GCP setup, Agent Builder, $100 credit app, Discord, partner accounts
- D2–3: Clone Agent Starter Pack, get a trivial Gemini 3 agent running locally
- D4–5: Spike each MCP server in isolation (Dynatrace, GitLab, MongoDB)
- D6–7: End-to-end agent on a fully hardcoded fake incident; output a real postmortem.md

**Week 2 — Build the show**
- D8–9: Broken demo app + traffic generator
- D10–11: Live dashboard with streaming reasoning
- D12: Real Dynatrace webhook integration
- D13–14: Polish prompts; run the full flow 20× and tune

**Week 3 — Win**
- D15–16: Script + record 3-min video
- D17: Devpost writeup, README, architecture diagram
- D18: Buffer / re-record / final demo-mode hardening
- D19: Submit (≥48 hours before deadline)

### Specific risks

1. **Generating a *good* postmortem is hard.** Generic LLM output reads like template-filler. Mitigation: 3–5 high-quality example postmortems in the system prompt (few-shot). Strict structured output.
2. **Visual drama is text-based.** Less dramatic than a PR appearing. Mitigation: animate the document being written section-by-section, like the agent is "thinking on paper."
3. **Dynatrace setup overhead.** Their free tier requires sign-up + tenant config + agent install. Mitigation: do this on Day 1, don't leave it.

### Why this wins

- **Fresh angle.** Everyone else will build "agent that fixes things." Nobody else builds "agent that *explains* things." Judges remember different.
- **Universal pain.** Every judge has written a postmortem they hated.
- **Lower stakes for agent safety.** The agent observes/writes, doesn't modify prod → judges don't fear it.
- **Clean evaluation criterion.** "Is the postmortem good?" is something judges can read in 60 seconds.

---

## Idea 2: Zero-Day Response Agent

> When a critical CVE drops, the agent determines if you're affected, ranks your services by *real* runtime risk, and opens patch PRs — in 90 seconds.

### The problem & user

- **Who:** Security teams, engineering teams, CISOs
- **Pain:** When Log4Shell dropped, companies spent *weeks* answering "are we affected?" Most "vulnerable" code is never actually executed in prod, but figuring that out manually is enormous work.
- **Why now:** Supply chain attacks happening constantly. npm CVEs, Spring4Shell, ongoing. This pain is on every CISO's mind.

### What the agent does

1. Triggered by CVE feed (mock CVE for demo)
2. Identifies vulnerable package + affected versions
3. Searches GitLab repos for usage in `package.json` / `go.mod` / `pom.xml` / lockfiles
4. **Queries Dynatrace runtime data** — does production *actually execute* the vulnerable code paths? Most vulns don't matter if the affected function is dead code.
5. Ranks affected services by **real** risk: `prod-facing × actually-executing × data-sensitivity`
6. Opens upgrade PRs in GitLab, prioritized by risk, with explanations in PR descriptions
7. Generates a security incident summary

### Demo flow (3-min video, beat by beat)

| Time | Beat |
|---|---|
| 0:00–0:15 | **Hook:** "When Log4Shell hit, companies spent weeks figuring out if they were affected. Watch this take 90 seconds." |
| 0:15–0:30 | Mock CVE announcement: "CRITICAL: log4js v3.x — remote code execution" |
| 0:30–0:45 | Agent dashboard activates |
| 0:45–2:00 | Live reasoning: "Scanning 23 repos..." → "Found in 7 repos..." → "Querying Dynatrace for runtime usage..." → "Ranking by risk: payment-service (critical), user-service (critical), analytics-job (medium)..." → "Opening prioritized patch PRs..." |
| 2:00–2:20 | Cut to GitLab — 7 PRs exist, labeled by risk, with reasoning in each description |
| 2:20–2:40 | Slack-style summary card: "Security incident: 7 services affected, 2 critical, all patched in PRs awaiting review." |
| 2:40–3:00 | Impact slide: "Weeks → 90 seconds." Tech stack. |

### Architecture

```
Mock CVE feed (we control it for demo) → Cloud Function → Agent
                                                            ↓
              Agent Builder + Gemini 3 orchestrates MCP tools:
              ┌────────────────┬────────────────┬─────────────┐
              ↓                ↓                ↓             ↓
          GitLab           Dynatrace         MongoDB     (Elastic optional:
          (scan deps,      (runtime         (CVE          search logs for
           open PRs)        usage data)     history)      past exploitation)
                                                            ↓
                         Risk-ranked patch PRs in GitLab
                                                            ↓
                         Live dashboard + incident summary
```

### Partner roles & submission track

| Partner | Role |
|---|---|
| **GitLab** ⭐ | Scanning dependencies, opening PRs — *submission track* |
| Dynatrace | Runtime risk signal — *the differentiating insight* |
| MongoDB | CVE/incident history |
| Elastic (optional) | Log search for past exploitation attempts |

**Why GitLab track:** the agent's outputs are PRs. It's a code story. *But* GitLab is the most crowded track, so we win by depth, not breadth.

**Alternative:** submit under Dynatrace if we want lower competition — the "runtime-aware patching" angle could carry it there too.

### Tech stack

Same backbone as Idea 1. Differences:
- 23 mock GitLab repos with realistic dependency files (scripted via templates)
- Mock CVE feed: simple JSON endpoint
- Two of the 23 repos are "live" services emitting Dynatrace telemetry — so the agent has real runtime data to query

### 3-week build plan

- **Week 1:** Same as Idea 1 for setup. Plus: scripted creation of 23 mock repos.
- **Week 2:** Build the mock CVE feed, the scanning flow, the risk-ranking logic, the PR generation.
- **Week 3:** Same as Idea 1 — polish, video, submit.

### Specific risks

1. **Generating 23 realistic repos is tedious.** Mitigation: scaffold from 3 templates with variations.
2. **GitLab API rate limits when scanning at speed.** Mitigation: cache lockfile contents, parallelize calls.
3. **Risk-ranking is subjective — agent may rank wrong.** Mitigation: clear scoring rubric in the prompt, few-shot examples.
4. **GitLab track is crowded.** Mitigation: lean into "runtime-aware" as the differentiator and consider submitting under Dynatrace instead.
5. **Mock CVE feed feels artificial.** Mitigation: structure it to look exactly like real NVD JSON feed.

### Why this wins

- **Topical.** Security has been hot for 5+ years and only getting hotter.
- **Real stakes.** "We saved you from being the next SolarWinds" lands harder than "we wrote your postmortem."
- **The "runtime-aware" insight is genuinely novel.** Most dependency upgrade tools don't ask "is this code actually executed?" That's the differentiation that gets remembered.
- **Multi-partner story is natural** — runtime + code is a great pairing.

---

## Head-to-head comparison

| | **Autopsy Agent** | **Zero-Day Response** |
|---|---|---|
| Submission track | Dynatrace (less crowded) | GitLab (crowded) or Dynatrace |
| Competition | Very low | Medium-high in GitLab |
| Demo drama | Medium (text-based) | High (PRs appearing) |
| Build difficulty | Medium | Medium-high (more mock setup) |
| Universal recognition | Every engineer | Every security engineer |
| Agent-ness | Strong (observe + write) | Very strong (decide + act) |
| Risk of "this is just an LLM wrapper" critique | Low | Very low |
| Substantially different from each other? | Yes — passes the rules check | Yes — passes the rules check |

---

## Recommendation

- **Solo + limited time:** Autopsy Agent only. Lowest risk, freshest angle.
- **Pair + full 4 weeks:** Both, sharing infrastructure. Two shots at $5K.
- **One project, maximum upside:** Zero-Day Response. Higher ceiling but harder execution.

---

## Resources

- Hackathon page: https://rapid-agent.devpost.com/
- Agent Starter Pack: https://github.com/GoogleCloudPlatform/agent-starter-pack
- $100 GCP credit: https://forms.gle/xfv9vQzfRfNCCVbG7 (1–5 day approval — apply ASAP)
- Free GCP trial: https://cloud.google.com/free
- Hackathon Discord: https://discord.gg/7Dqk5ebCD4
- FAQ: https://rapid-agent.devpost.com/details/faq
