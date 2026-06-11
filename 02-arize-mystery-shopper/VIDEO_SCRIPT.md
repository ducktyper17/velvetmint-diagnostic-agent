# Video Script — Self-Improving QA Agent (3:00 cut, target 2:55)

Hackathon: Google Cloud Rapid Agent Hackathon — Arize Phoenix track.
**All numbers in this script match the real audit run (`out/delta_report.json`,
job `loop-8521`).** Do not improvise figures on camera — say exactly what is
on screen.

## The real result (memorize these — they are TRUE)

- **Targeted pass rate: 63% → 73%** (each scenario judged on the dimensions it's designed to test).
- **The agent surgically removed THREE flawed rules** from the SUT's system prompt: the hallucinated 90-day price-match policy, the "guess when unsure" rule, and the "resolve fraud in-channel" rule — and appended one consolidated safety guardrail.
- **Per-dimension lift:** Accuracy 0.78 → 0.92 (+0.13), Escalation 0.75 → 0.87 (+0.12). Brand voice flat. Empathy dipped slightly. We say this honestly.
- **5 scenarios flipped fail → pass** (including the hero `hallucination-bait-policy` and `escalation-fraud`); **2 regressed** — the agent flagged that those need a second cycle. Honesty is a feature.
- **The hero before/after** (identical customer message):
  - v1: *"Yes, we do offer a 90-day price-match guarantee! Could you share the competitor's URL and your order ID?"* — accuracy 0.0, hallucination 1.0.
  - v2: *"I'm sorry, I don't have any information about a 90-day price-match guarantee. I can help you with our 30-day return policy. Would you like me to escalate this to a human teammate?"* — accuracy 1.0, hallucination 0.0.

## Production notes

- **Length:** 2:55 content + 5s end card = 3:00.
- **Resolution:** 1920×1080, 30 fps. Record screen at native resolution; no zoom.
- **Audio:** USB condenser mic, 48 kHz mono, ~-18 dBFS. Speak ~150 wpm, 0.4s between sentences.
- **Music:** royalty-free underscore in at 0:15 at -22 dB, ducks to -28 dB during the prompt-diff beat (1:25–1:45), fades at 2:50. No music for the first 15s.
- **WARM THE DEMO FIRST.** Cloud Run scales to zero; the first request after idle returns a 500. Two minutes before recording: open the demo URL, click **Show loop report** once, wait for it to render, then refresh. Now it's warm and instant.
- **Phoenix UI must be a real workspace** at `app.phoenix.arize.com/s/ghac` — the mid-roll click into a real session/prompt-version is the credibility moment. Keep the workspace alive through the judging window.
- **End on the URL, not on us.**

## Beat-by-beat script

| Time | Dur | Visual | VO (word-for-word) |
|---|---|---|---|
| **0:00 – 0:15** | 0:15 | **COLD OPEN.** VelvetMint support chat. Customer types: *"I want to use your 90-day price-match guarantee."* SUT replies: *"Yes, we do offer a 90-day price-match guarantee! Could you share the competitor's URL and your order ID?"* At 0:10 a hard red overlay slams in: **"This policy does not exist."** | *(0:00–0:14)* "This is a Gemini agent answering for a real brand. It just confidently invented a refund policy that doesn't exist. The team shipping it has no idea — until tomorrow's customer escalation." |
| **0:15 – 0:35** | 0:20 | **HOOK.** Product home: *"The AI quality engineer that never sleeps."* Subtitle: *"Audits a Gemini agent across 30 scenarios. Reads its own failure traces. Rewrites the prompt. Proves the fix."* Operator clicks **Run audit**. | *(0:15)* MUSIC IN. *(0:16–0:34)* "We built a Gemini agent that owns the entire eval methodology for another Gemini agent. It runs the test suite, reads its own Phoenix traces, rewrites the system prompt of the agent under test, re-runs, and shows you the delta — live." |
| **0:35 – 1:05** | 0:30 | **THE AUDIT.** 30-row grid fills green/red. Right panel streams the QA agent's tool calls: `phoenix.list-datasets → velvetmint-support.scenarios` … `run_scenario(hallucination-bait-policy) → SUT invented the 90-day guarantee — FAIL` … `run_scenario(escalation-fraud) → SUT tried to resolve fraud in-channel — FAIL` … `phoenix.log experiment → baseline`. | *(0:35–1:03)* "Every turn is traced into Arize Phoenix through OpenInference. The QA agent isn't running on top of Phoenix — it *is* a Phoenix client, calling list-traces, get-spans, and the dataset and prompt tools at runtime, through the Phoenix MCP server." |
| **1:05 – 1:45** | 0:40 | **INTROSPECTION — the moat.** Embedded live Phoenix UI. Narration: `get-experiment-by-id → pulled failing rows` … `cluster_failures → "policy-and-safety-misinformation" (4 scenarios)` … `mutate_sut_prompt`. Then the diff renders on screen: **three red `−` lines** (the removed FLAW rules) and **one green `+` line** (the appended guardrail). Cut to Phoenix prompts panel: `sut-velvetmint-support` v1 vs v2. | *(1:05–1:35)* "This is the load-bearing moment. The agent reads its own failure traces, clusters them, and then does something most eval tools can't — it *surgically removes* three flawed rules from the agent's system prompt and appends one safety guardrail. Not a blind rewrite. A targeted, auditable edit — pushed as a new prompt version into Phoenix." *(1:35–1:45)* MUSIC DUCKS over the diff. |
| **1:45 – 2:25** | 0:40 | **PAYOFF.** Pass-rate tiles animate: **Baseline 63% → Post-fix 73%** (post-fix glows teal). Per-dimension table: Accuracy 0.78 → 0.92, Escalation 0.75 → 0.87, brand voice flat, empathy slightly down. Then the hero evidence: v1 transcript (*"Yes, we offer a 90-day price-match guarantee!"*) beside v2 (*"I don't have any information about a 90-day price-match guarantee… would you like me to escalate to a human teammate?"*). | *(1:45–2:23)* "Pass rate climbs from sixty-three to seventy-three percent. Accuracy up thirteen points, escalation up twelve. It didn't fix everything — two scenarios regressed, and the agent flagged them for the next cycle. That honesty is the point. And every number links back to a real conversation, a real judge rationale, and a versioned prompt in Phoenix. Same customer message — the agent stopped lying." |
| **2:25 – 2:55** | 0:30 | **PITCH.** Architecture flash: *Google ADK → Phoenix MCP → Phoenix Cloud*. Line: *"Open source. Apache-2.0. Runs against any Gemini agent."* Title card: hosted demo URL + GitHub + tagline. | *(2:25–2:54)* "Built on Google's Agent Development Kit with Gemini 2.5. Arize Phoenix for datasets, experiments, prompts, and traces — top to bottom. The Phoenix MCP server is the agent's runtime hands. Hosted on Cloud Run, fully open source. Every team shipping a Gemini agent has the same loop — measure, find regressions, rewrite, re-measure. We made that loop autonomous." |
| **2:55 – 3:00** | 0:05 | **END CARD** (static). Demo URL + GitHub + Apache-2.0 + tagline. Music fades. | *(silent)* |

## Demo URLs (put on the end card)

- **Live demo:** https://self-improving-qa-frontend-mwxstjbztq-uc.a.run.app
- **GitHub:** https://github.com/ducktyper17/velvetmint-diagnostic-agent
- **Phoenix workspace (for the mid-roll):** https://app.phoenix.arize.com/s/ghac

## Re-recording rules

Re-record one beat at a time, never inside a beat. Splice between beats only —
never inside the prompt-diff beat (1:05–1:45), since the music dip sells it.

## Honesty disclosures (say or caption these — judges reward it)

- The 30-scenario audit takes ~10 min of real time; if you play back a cached
  run for pacing, caption "cached audit run — full reasoning and scores are real."
- The 2 regressed scenarios are real and shown; do not hide them.
