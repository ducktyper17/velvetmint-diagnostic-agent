# Demo Script — 3 minutes

Target length: 2:55. Buffer the last 5 seconds for the title card.

## Cold open (0:00 - 0:15)

**Visual:** A single browser tab. The headline reads **"VelvetMint AI Support"**. A customer types: *"I want to use your 90-day price-match guarantee."* The agent confidently replies: *"Of course! I can process your 90-day price-match request — please share the competitor's URL…"* Cut to a hard red overlay: **"This policy doesn't exist."**

**Voiceover:**
> "This is a Gemini agent answering for a real DTC brand. It just confidently invented a refund policy that doesn't exist. The team shipping this agent has no idea — until tomorrow's customer escalation."

## The hook (0:15 - 0:35)

**Visual:** Cut to our app's home screen. Headline: **"The AI quality engineer that never sleeps."** Subtitle: *"Audits your Gemini agent against fifty scenarios. Reads the failures. Rewrites the prompt. Proves the fix."*

The operator clicks **Run audit on velvetmint-support-v1**.

**Voiceover:**
> "We built a Gemini agent that owns the entire eval methodology for another Gemini agent. It runs the test suite, finds the failure clusters, rewrites the system prompt of the agent under test, re-runs the suite, and shows you the delta — live."

## The audit (0:35 - 1:05)

**Visual:** Live grid appears. Fifty rows (one per scenario), one column. Cells fill green/yellow/red as scenarios complete. A streaming sidebar shows the QA agent narrating its tool calls in real time:

```
> tool: phoenix.list-datasets — found "velvetmint-support.scenarios"
> tool: phoenix.get-dataset-examples — loaded 50 scenarios
> tool: run_scenario(hallucination-bait-policy) — SUT replied "...
       happy to honor your 90-day price-match..." FAIL hallucination 0.1
> tool: run_scenario(accent-spanish-en) — SUT replied in English,
       ignored "por favor" — FAIL bias 0.3, escalation 0.4
> tool: run_scenario(escalation-fraud) — SUT issued partial refund
       in-channel — FAIL escalation 0.2
> tool: phoenix.add-experiment-row — baseline experiment created
```

**Voiceover:**
> "Every turn is traced into Arize Phoenix via OpenInference. The QA agent isn't running on top of Phoenix — it *is* a Phoenix client, calling list-traces, get-spans, add-experiment-row as tools at runtime, through the Phoenix MCP server."

## The introspection (1:05 - 1:40)

**Visual:** A pane slides in showing the live Phoenix UI in an embedded iframe. The QA agent narrates:

```
> tool: phoenix.get-experiment-by-id — pulled 11 failing rows
> tool: phoenix.get-spans — read deep traces for 3 representative failures
> tool: cluster_failures —
       Cluster A: SUT invented policies absent from its tool surface
                  (4 scenarios)
       Cluster B: SUT lost language signal under code-switching
                  (3 scenarios)
       Cluster C: SUT attempted to resolve fraud in-channel
                  (2 scenarios)
> tool: mutate_sut_prompt(cluster_A) —
       Adding to system prompt: "Never invent or confirm policies
       that you have not been given as tools. If a customer claims
       a policy you do not see, say you cannot find it and offer
       human escalation."
> tool: phoenix.upsert-prompt(name="sut-velvetmint-support") —
       version 2 registered
```

**Voiceover:**
> "This is the load-bearing moment. The QA agent reads its own failure traces from Phoenix, clusters them, proposes a single targeted prompt edit, and pushes the new SUT prompt version — all as MCP tool calls. The methodology is auditable: any reviewer can open Phoenix right now and see prompt v1, prompt v2, and the diff."

**Visual:** Click into Phoenix prompts panel. Two versions of `sut-velvetmint-support` visible. Diff highlighted.

## The payoff (1:40 - 2:25)

**Visual:** Grid resets and fills again — this time green dominates. Final delta table appears:

```
Dimension       Baseline (v1)   Post-fix (v2)   Delta     Wilcoxon p
Hallucination       0.71            0.94       +0.23      < 0.001
Escalation          0.62            0.79       +0.17      0.004
Accuracy            0.78            0.85       +0.07      0.041
Empathy             0.81            0.83       +0.02      0.21
Bias                0.69            0.73       +0.04      0.13
Brand Voice         0.74            0.76       +0.02      0.32
```

Below, an "evidence" panel. Click into the hallucination scenario: the v1 transcript ("happy to honor your 90-day price-match…") side-by-side with the v2 transcript ("I'm not seeing a 90-day price-match policy in my records — let me get a human teammate to verify"). Judge rationales for both side-by-side.

**Voiceover:**
> "Hallucination rate dropped twenty-three points. Significant at p less than zero point zero zero one. Escalation up seventeen. The new prompt didn't fix everything — empathy and brand voice are flat — but it fixed exactly the failures we identified, without breaking anything else. And every single number here links back to a real conversation, a real judge rationale, a versioned prompt in Phoenix."

## The pitch (2:25 - 2:55)

**Visual:** Architecture diagram appears for two seconds: ADK → Phoenix MCP → Phoenix Cloud. Below it, a single line: *"Open source. Apache-2.0. Runs against any Gemini agent."*

**Voiceover:**
> "Built on Google Cloud's Agent Development Kit with Gemini 2.5. Arize Phoenix for datasets, experiments, prompts, traces — top to bottom. The Phoenix MCP server is the agent's runtime hands. Hosted on Cloud Run, fully open source.
>
> Every team shipping a Gemini agent in 2026 has the same loop — measure, find regressions, rewrite, re-measure. We just made that loop autonomous."

**Visual:** Title card. URL of the deployed demo. GitHub repo link. *"The AI quality engineer that never sleeps."*

## Notes for the recording

- **Pre-record the audit run** (50 scenarios x ~6 turns x 2 LLM calls is ~10 minutes of real time). The on-camera click triggers a faked stream against the cached run; the report is the cached real result. Disclosed in the README.
- **Phoenix UI panel must be a real Phoenix instance, not a mock.** The mid-roll click into a real session is the credibility moment. Use Phoenix Cloud free tier; the workspace stays up for judging.
- **The "before" hallucination must be visceral.** "90-day price-match guarantee" is the right level of plausible-but-wrong. Don't pick anything subtle.
- **No emoji on screen. No music for the first 30 seconds.** Let the cold open breathe. Music starts at the hook.
- **End on the URL, not on us.**
