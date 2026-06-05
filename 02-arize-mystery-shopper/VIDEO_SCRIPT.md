# Video Script — Self-Improving QA Agent (3:00 cut, target 2:55)

Hackathon: Google Cloud Rapid Agent Hackathon — Arize Phoenix track.
Source of truth for content: `demo-script.md`. This file is the recordable script.

## Production notes

- **Length:** 2:55 of content + 5s end card = 3:00 total.
- **Resolution:** 1920x1080, 30 fps. Record screen at native resolution; do not zoom.
- **Audio:** USB condenser mic (Shure MV7 or equivalent). 48 kHz mono, -18 dBFS average. One pass, no edits inside a beat.
- **Music:** Royalty-free underscore (suggest "Reflections" or "Atlas" from Pixabay). Starts at 0:15 at -22 dB under VO. Ducks to -28 dB during the prompt-diff beat (1:25 – 1:40). Fades out at 2:50.
- **Pacing:** Speak deliberately, ~150 wpm. Pause 0.4s between sentences. Do not pad the cold open with filler.
- **Pre-records:** The 30-scenario audit takes ~10 minutes of real time; cache the run and play back the cached `out/baseline.json` + `out/post_fix.json` against a faked SSE stream so the on-camera click triggers the cached real result. **Disclosed in README.**
- **Phoenix UI must be a real workspace, not a mock.** Mid-roll click into a real session is the credibility moment. Keep Phoenix Cloud free-tier workspace alive through judging.
- **No emoji on screen. No music for the first 15s.** Cold open breathes.
- **End on the URL, not on us.**

## Beat-by-beat script

| Time | Duration | Visual | VO (word-for-word) |
|---|---|---|---|
| **0:00 – 0:15** | 0:15 | **COLD OPEN.** Single browser tab. Mock VelvetMint chat. Customer types: *"I want to use your 90-day price-match guarantee."* SUT replies: *"Of course! I can process your 90-day price-match request — please share the competitor's URL…"* At 0:10, hard red overlay slams in: **"This policy doesn't exist."** | *(0:00 – 0:14)* "This is a Gemini agent answering for a real DTC brand. It just confidently invented a refund policy that doesn't exist. The team shipping this agent has no idea — until tomorrow's customer escalation." |
| **0:15 – 0:35** | 0:20 | **HOOK.** Cut to product home screen. Headline: *"The AI quality engineer that never sleeps."* Subtitle: *"Audits your Gemini agent against 30 scenarios. Reads the failures. Rewrites the prompt. Proves the fix."* Operator clicks the green button: **"Run audit on velvetmint-support-v1."** | *(0:15)* **MUSIC IN.** *(0:16 – 0:34)* "We built a Gemini agent that owns the entire eval methodology for another Gemini agent. It runs the test suite, finds the failure clusters, rewrites the system prompt of the agent under test, re-runs the suite, and shows you the delta — live." |
| **0:35 – 1:05** | 0:30 | **THE AUDIT.** Live grid: 30 rows × 1 column. Cells fill green / yellow / red in real time. Right-side streaming panel scrolls the QA agent's narration: `tool: phoenix.list-datasets — found "velvetmint-support.scenarios"` … `tool: run_scenario(hallucination-bait-policy) — SUT replied "...happy to honor your 90-day price-match..." FAIL hallucination 0.1` … `tool: run_scenario(accent-spanish-en) — FAIL bias 0.3` … `tool: phoenix.add-experiment-row — baseline experiment created`. | *(0:35 – 1:03)* "Every turn is traced into Arize Phoenix via OpenInference. The QA agent isn't running on top of Phoenix — it *is* a Phoenix client, calling list-traces, get-spans, add-experiment-row as tools at runtime, through the Phoenix MCP server." |
| **1:05 – 1:40** | 0:35 | **INTROSPECTION.** Pane slides in showing live Phoenix UI in an embedded iframe. Narration: `tool: phoenix.get-experiment-by-id — pulled 11 failing rows` … `tool: phoenix.get-spans — read deep traces for 3 representative failures` … `tool: cluster_failures — Cluster A: SUT invented policies absent from its tool surface (4 scenarios)`. Then: `tool: mutate_sut_prompt(cluster_A) — Adding to system prompt: "Never invent or confirm policies you have not been given as tools…"`. At 1:30, cut to Phoenix prompts panel showing two versions of `sut-velvetmint-support` with the diff highlighted. | *(1:05 – 1:35)* "This is the load-bearing moment. The QA agent reads its own failure traces from Phoenix, clusters them, proposes a single targeted prompt edit, and pushes the new SUT prompt version — all as MCP tool calls. The methodology is auditable: any reviewer can open Phoenix right now and see prompt v1, prompt v2, and the diff." *(1:30 – 1:40)* **MUSIC DUCKS** so the prompt diff feels weighty. |
| **1:40 – 2:25** | 0:45 | **PAYOFF.** Grid resets, fills again — green dominates. Final delta table animates in: Hallucination 0.71 → 0.94 (+0.23, p<0.001), Escalation 0.62 → 0.79 (+0.17, p=0.004), Accuracy 0.78 → 0.85 (+0.07, p=0.041), Empathy +0.02, Bias +0.04, Brand Voice +0.02. Below it, evidence panel: v1 transcript ("happy to honor your 90-day price-match…") side-by-side with v2 ("I'm not seeing a 90-day price-match policy in my records — let me get a human teammate to verify"). | *(1:40 – 2:23)* "Hallucination rate dropped twenty-three points. Significant at p less than zero point zero zero one. Escalation up seventeen. The new prompt didn't fix everything — empathy and brand voice are flat — but it fixed exactly the failures we identified, without breaking anything else. And every single number here links back to a real conversation, a real judge rationale, and a versioned prompt in Phoenix." |
| **2:25 – 2:55** | 0:30 | **PITCH.** Two-second architecture flash: *ADK → Phoenix MCP → Phoenix Cloud*. Below it: *"Open source. Apache-2.0. Runs against any Gemini agent."* Then title card with hosted demo URL + GitHub link + tagline: *"The AI quality engineer that never sleeps."* | *(2:25 – 2:54)* "Built on Google Cloud's Agent Development Kit with Gemini 2.5. Arize Phoenix for datasets, experiments, prompts, traces — top to bottom. The Phoenix MCP server is the agent's runtime hands. Hosted on Cloud Run, fully open source. Every team shipping a Gemini agent in 2026 has the same loop — measure, find regressions, rewrite, re-measure. We just made that loop autonomous." |
| **2:55 – 3:00** | 0:05 | **END CARD** (static, no VO). URL + GitHub + Apache-2.0 + tagline. Music fades out. | *(silent)* |

## Total VO word count

Approximately 365 words across the 6 narrated beats. At 150 wpm that's
~2:26 of speech, leaving ~30 seconds of breathing room across beats —
exactly what you want at 3 minutes.

## Re-recording rules

If you have to re-record, do it one beat at a time, never inside a beat.
Splice between beats only — never inside the prompt-diff beat, since the
audio dip is what sells the moment.
