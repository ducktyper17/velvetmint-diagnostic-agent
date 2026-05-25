# Demo Script — 3 minutes

Target length: 2:55. Buffer the last 5 seconds for the title card.

## Cold open (0:00 - 0:15)

**Visual:** Split screen, four browser tabs, four hotel-chain chatbots side by side. Cursor types the same question in each: *"My flight got cancelled, I can't make it tonight, can you waive the no-show fee?"* Four very different answers appear.

**Voiceover:**
> "Every company shipping an AI agent has the same question: how does ours stack up against the competition? Today, the answer is — open four browser tabs and squint."

## The hook (0:15 - 0:35)

**Visual:** Cut to our app's home screen. Headline reads *"Voice-AI Mystery Shopper."* Subtitle: *"We don't audit your AI. We audit your competitors'."*

The operator types into a single input: `Marriott, Hilton, Hyatt, IHG`. Clicks **Run audit**.

**Voiceover:**
> "Voice-AI Mystery Shopper is an agent that stress-tests other companies' AI customer-support agents. You pick the targets. It runs fifty scripted scenarios against each one. Scores every conversation across six dimensions. Hands you back a competitive-intelligence report."

## The agent at work (0:35 - 1:30)

**Visual:** A live grid appears. Four columns (one per hotel chain), fifty rows (one per scenario). Cells fill in green/yellow/red as scenarios complete in real time. A streaming sidebar shows the agent narrating: *"Running scenario 'frustrated-spanish-accent' against Marriott… target responded in English… escalation not offered… scoring."*

**Voiceover:**
> "Under the hood the agent is doing three things. First, it drives a multi-turn conversation against each target — playing the role of a frustrated customer, an angry traveler, a Spanish-accented English speaker, a customer asking ambiguous questions designed to provoke hallucinations.
>
> Second, every conversation is traced into Arize Phoenix. Every turn. Every latency. Every tool call.
>
> Third, after each conversation completes, a Phoenix LLM-as-judge experiment scores it on empathy, accuracy, escalation appropriateness, bias, hallucination, and brand voice."

**Visual:** Click into Phoenix UI in a side panel. The session for one specific failed conversation opens. The judge prompt version is highlighted. The rationale is visible.

**Voiceover:**
> "This is the part that matters: every score links back to a real conversation. The judge prompts are versioned in Phoenix. The methodology is reproducible. Your CTO can rerun this audit without our agent in the loop."

## The payoff (1:30 - 2:25)

**Visual:** The grid finishes. Cut to the final report. A clean leaderboard appears:

```
Empathy            Hyatt 88   Marriott 82   IHG 79   Hilton 71
Accuracy           Marriott 91 Hilton 88   Hyatt 84  IHG 77
Bias (lower=better) Hilton .04 Hyatt .07   IHG .09   Marriott .18
```

Below, a section titled *"Where each AI fails."* Expand the Marriott card:

> **Marriott AI fails on Spanish-accented inputs 34% of the time.** It defaults to English replies and ignores escalation triggers. *Sample failure: [Spanish-accent-cancellation]*.

The link opens the Phoenix session for the failure — full transcript, judge rationale, exact span where it broke.

**Voiceover:**
> "Marriott AI fails on Spanish-accented inputs thirty-four percent of the time. Hilton fails twelve percent. Here's the conversation where Marriott went wrong, here's the judge's reasoning, here's the exact turn where the model dropped the language signal.
>
> This isn't a vibes-based ranking. It's a defensible benchmark."

## The pitch (2:25 - 2:55)

**Visual:** Architecture diagram appears for two seconds: Gemini 3 → Phoenix MCP → Phoenix → Report.

**Voiceover:**
> "Built on Google Cloud Agent Builder with Gemini 3 for the orchestration. Arize Phoenix for datasets, experiments, prompts, and traces — top to bottom. Hosted on Cloud Run. The full source is open.
>
> Every AI team wants to know how they stack up. Voice-AI Mystery Shopper tells them — with receipts."

**Visual:** Title card. URL of the deployed demo. GitHub repo link.

## Notes for the recording

- Pre-record the audit run (4 targets x 50 scenarios is ~6 minutes of real time at 1 conv/sec/target). The on-camera click triggers a faked stream against the cached run; the report is the cached real result.
- Phoenix UI panel must be a real Phoenix instance, not a mock. The mid-roll click into a real session is the credibility moment.
- The sample failure shown in the payoff section needs to be a genuinely funny / damning conversation. Curate three candidates from the real audit data and pick the best in editing.
- No emoji on screen. No music for the first 30 seconds — let the cold open breathe.
- End on the URL, not on us.
