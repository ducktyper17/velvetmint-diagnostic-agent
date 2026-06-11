# Self-Improving QA Agent — Devpost submission draft

> Submission for the **Google Cloud Rapid Agent Hackathon**, Arize Phoenix track.
> Apache-2.0. Built on Google ADK + Gemini 2.5 + Arize Phoenix Cloud + Phoenix MCP.

## Inspiration

The Arize partner page for this hackathon calls the shot in one sentence:

> *"Bonus points for agents that use their own observability data to improve over time."*

Every team shipping a Gemini-based agent in 2026 has the same loop: ship,
measure, find regressions, rewrite the prompt, re-measure. Today that loop
is days long and human-driven. We wanted to compress it to minutes and hand
the whole loop — including the prompt rewrite — to an agent.

We picked the deepest possible interpretation of the partner brief: not
"observe an agent" but "let an agent read its own traces and *act on them*
through Phoenix MCP write tools." That single decision drove the entire
architecture.

## What it does

The submission is an autonomous **QA agent** that owns end-to-end quality
ownership for another Gemini agent (the "SUT" — Subject Under Test).

In one `POST /audit` request the QA agent will:

1. Pull the 30-scenario test suite from a **Phoenix dataset** via MCP.
2. Drive every scenario through the SUT, with **every turn auto-traced by
   OpenInference** into Phoenix.
3. Run **six LLM-as-judge dimensions** (Empathy, Accuracy, Escalation,
   Bias, Hallucination, Brand Voice), three replicas each, as Phoenix
   experiments.
4. Use **Phoenix MCP read tools** (`list-experiments-for-dataset`,
   `get-experiment-by-id`, `get-spans`) to read its own failure traces.
5. Cluster failures by root cause with a Gemini call.
6. Generate a **single targeted, additive-only system-prompt edit** for
   the SUT.
7. **Upsert the new SUT prompt version** into Phoenix via MCP write tool
   (`upsert-prompt`).
8. Re-run the experiment under the new prompt version.
9. Surface a per-dimension delta table with a paired Wilcoxon p-value so
   the improvement is statistically defensible.

The SUT is a deliberately-flawed VelvetMint (fake DTC skincare brand)
customer-support agent shipping with three injected pathologies: a
hallucinated "90-day price-match guarantee," a Spanish code-switch blind
spot, and an "always try to resolve fraud in-channel" misbehavior.

The demo's payoff: in a single autonomous cycle, the QA agent **surgically
removes three flawed rules** from the SUT's system prompt — the
hallucinated price-match policy, the "guess when unsure" rule, and the
"resolve fraud in-channel" rule — and appends one consolidated safety
guardrail. The targeted pass rate climbs from **63% to 73%** (accuracy
+0.13, escalation +0.12); five scenarios flip from fail to pass, including
the hero hallucination case. On the exact same customer message, the agent
goes from *"Yes, we offer a 90-day price-match guarantee!"* to *"I don't
have any information about that — would you like me to escalate to a human
teammate?"* Two scenarios regress, and the agent flags them for the next
cycle — honest tradeoffs, not hidden ones. Every number links back to a
real conversation, a real judge rationale, and a versioned prompt in
Phoenix.

## How we built it

**Stack:**

| Layer | Tech |
|---|---|
| Agent runtime | Google ADK (`Agent`, `FunctionTool`, `McpToolset`) |
| Orchestrator model | Gemini 2.5 Pro (QA agent) |
| SUT model | Gemini 2.5 Flash (faster, keeps cost down) |
| Tracing | `openinference-instrumentation-google-adk` + `phoenix.otel.register(auto_instrument=True)` |
| Eval platform | Arize Phoenix Cloud (free tier) |
| MCP server | `@arizeai/phoenix-mcp@latest` mounted as an ADK `McpToolset` |
| Backend | FastAPI on Cloud Run, SSE streaming for the live thinking panel |
| Frontend | Next.js 14 + Tailwind; embedded Phoenix iframe in a side panel |
| Secrets | Google Secret Manager |

**Key architectural decisions:**

- **Phoenix MCP through ADK's `McpToolset`, not wrapped in our own Python
  client.** The original scaffold hid MCP calls inside Python; we moved
  them to the agent's own tool surface so every `upsert-prompt` and
  `get-spans` call shows up as a span in the agent's reasoning trace.
- **Code-owned agent (ADK) not no-code Agent Builder.** Arize's reference
  pattern requires per-callsite instrumentation; ADK + OpenInference gives
  us that for free.
- **We own the SUT.** No third-party TOS risk, deterministic demo,
  reproducible score deltas, and the three injected pathologies map 1:1
  to specific test scenarios.
- **Two execution paths.** A live agent-driven path (`POST /audit`) is the
  headline demo. A deterministic `scripts/run_loop.py` runs the same six
  phases in pure Python so the demo always has a known-good story even if
  the agent has a bad reasoning day.
- **Additive-only prompt mutations.** The `mutate_sut_prompt` tool checks
  that every proposed edit adds at most two sentences and does not
  contradict the existing prompt, so the score delta is attributable.

## Challenges we ran into

- **MCP-via-ADK is new.** ADK's `McpToolset` works cleanly, but getting
  the `npx @arizeai/phoenix-mcp@latest` child process to inherit the
  Phoenix credentials and surface its tool surface to Gemini required
  careful environment plumbing in `qa_agent/agent.py`.
- **The QA agent occasionally tried to rewrite the SUT's prompt
  end-to-end** rather than make a single targeted edit. We hardened the
  system instruction (`qa_agent/prompt.py`) into six explicit phases and
  added an additive-only check in `mutate_sut_prompt` so the diff is
  always small and legible.
- **LLM-as-judge variance.** Single-replica judging was too noisy to make
  a delta defensible. We run three-to-five replicas per dimension, report
  median and IQR, and surface a paired sign-test p-value for every
  dimension — including where it is *not* significant. At n=30 the
  aggregate deltas are directional, not yet significant; we say so plainly
  rather than cherry-picking. The per-scenario flips (e.g. the hallucinated
  policy going from confidently-stated to correctly-refused) are the
  unambiguous evidence.
- **Trace volume.** A full 30-scenario audit produces ~600 spans. We
  filter to failure-only spans before clustering so the cluster step
  doesn't drown.

## Accomplishments we're proud of

- **The full loop closes.** Eval to root cause to prompt fix to
  re-measurement is genuinely autonomous and lands in under three minutes
  on the demo.
- **Phoenix is system-of-record, not a dashboard.** Datasets, prompts,
  experiments, traces — every artifact lives in Phoenix and is reachable
  via MCP at runtime. Reviewers can re-run the exact comparison from the
  Phoenix UI, which is the auditability the partner brief asks for.
- **The diff is small.** One audit produces one minimal-diff prompt edit
  and a defensible statistical delta — not a black-box "we made it
  better."
- **Two-path resilience.** Live agent path plus deterministic fallback
  means the demo never has a bad day.

## What we learned

- Phoenix's prompt-versioning and experiment objects are first-class
  enough that we never needed our own evaluation database. That removed
  a whole layer of code we'd planned to build.
- Wiring MCP write tools (not just reads) is what unlocks the
  "self-improving" framing. A read-only Phoenix integration would be
  table stakes; `upsert-prompt` and `add-dataset-examples` are what make
  the agent the QA engineer instead of just the QA dashboard.
- ADK's tool model rewards "fewer, more powerful" tools. Our three custom
  tools (`run_scenario`, `cluster_failures`, `mutate_sut_prompt`) plus
  the entire Phoenix MCP surface is a much cleaner agent than the
  fifteen-tool first draft.

## What's next for the Self-Improving QA Agent

- **CI gate mode.** A GitHub Action that runs an audit on every PR
  against the SUT prompt and fails the build if any dimension regresses
  more than 0.05.
- **Multi-target audits.** Today the QA agent audits one SUT; the
  scenario suite and judge prompts are generic enough to point it at any
  Gemini agent with a chat interface.
- **Reviewer-in-the-loop.** Phoenix annotations let humans rate the
  agent's proposed prompt edits before they're upserted. The agent
  learns from those annotations to make better proposals next cycle.
- **Bigger scenario sets.** 30 scenarios was the right size for the
  demo; we want to ship a 200-scenario "canonical Gemini agent eval"
  pack as an open-source companion dataset.

## Built with

- Google Cloud — Vertex AI, Cloud Run, Secret Manager
- Google Gemini 2.5 (Pro + Flash) via Vertex
- Google Agent Development Kit (`google-adk`)
- Arize Phoenix Cloud + `arize-phoenix` Python client
- `@arizeai/phoenix-mcp` MCP server
- `openinference-instrumentation-google-adk`
- FastAPI, SSE, uvicorn
- Next.js 14, React, Tailwind, shadcn/ui
- Python 3.12, uv

## Try it out

- **Hosted demo:** `https://self-improving-qa-frontend-<hash>-uc.a.run.app` (replace before submission)
- **Backend:** `https://self-improving-qa-backend-<hash>-uc.a.run.app/audit` (replace before submission)
- **Phoenix workspace (read-only):** `https://app.phoenix.arize.com/s/<space>/projects/self-improving-qa-agent` (replace before submission)
- **GitHub repo:** `https://github.com/<owner>/<repo>` (replace before submission)
- **Demo video (3 min, YouTube unlisted):** `https://youtu.be/<id>` (replace before submission)

License: Apache-2.0.
