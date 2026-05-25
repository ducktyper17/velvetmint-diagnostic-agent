# The trial-expiry problem (and our plan)

Several partner trials are 14 days. Judging runs June 22 – July 6, 2026. The hosted demo URL must remain working during that window or judges may score us as broken in Stage 1 (pass/fail on completeness).

## The numbers

| Item | Length | If started May 24 → expires | Judging starts June 22 |
|---|---|---|---|
| GCP free trial | 90 days | August 22 | ✅ Safe |
| GCP $100 credit | 90 days from approval | mid-Aug or later | ✅ Safe |
| **Fivetran free trial** | **14 days** | **June 7** | ❌ **Expired before judging** |
| MongoDB Atlas free tier (M0) | Unlimited (always-free) | n/a | ✅ Safe |
| Elastic Cloud trial | 14 days | June 7 | ❌ Expired (irrelevant — we're not on Elastic track) |
| Dynatrace trial | 15 days | June 8 | ❌ Expired (irrelevant) |

**The Fivetran trial expiry is a real risk for us.** If our demo depends on a live Fivetran account during judging, and the trial expires June 7, the demo URL is dead by June 22.

## How we mitigate (architecture decision, locked in now)

The agent has **two execution modes**, controlled by an env var:

### Mode A: `LIVE` (during build, May 24 – June 7)

The agent makes real calls against the Fivetran MCP server. Real connectors get created, real syncs run, real data lands in BigQuery. This is the development mode. Used to validate the MCP integration works end-to-end.

### Mode B: `DEMO` (June 7 onward, including judging)

The agent replays a recorded session. Specifically:
- During the LIVE phase (May 24 – June 6) we record 5–10 high-quality diagnostic runs of the agent against the synthetic VelvetMint data. Each recording captures the full trace: every Gemini reasoning step, every Fivetran MCP tool call, every BigQuery query, every output.
- The recordings live in MongoDB Atlas (always-free tier) and are deterministic — same input question → replay the cached trace, streamed via SSE at realistic pacing.
- The frontend looks identical to LIVE mode. Judges see "the agent setting up connectors, syncing data, querying, diagnosing." It really did all of that during recording. We're just replaying.

This is **honest** — not a fake. The agent really did the work; we're just playing back the trace because Fivetran's trial expired. The README will disclose this clearly.

## Asking Fivetran about extended trials (Tuesday May 27 webinar)

Before we commit to demo mode, we'll ask in the [Fivetran webinar on May 27](https://go.fivetran.com/webinars/hackathon-qa-power-your-ai-agent-with-data-fivetran-and-google-cloud):

1. Is there an extended trial available for hackathon participants?
2. Can we get a sandbox/free-tier account that runs through July?
3. Are there specific MCP-write-mode tools (like `create_connection`) gated behind paid plans?

If Fivetran says yes to an extended trial, we use LIVE mode for the demo too. If no, we use DEMO mode and disclose.

**Forum post we should write tonight or tomorrow**: there's already a [related thread](https://rapid-agent.devpost.com/forum_topics) on Dynatrace trial expiry. We could ask in our own thread on Fivetran. Worth doing — the judges read these threads.

## What this means for the build plan

- **Days 1–7**: develop in LIVE mode. Make everything real.
- **Days 8–13**: integration polish, but ALSO record 5–10 reference traces in MongoDB Atlas.
- **Day 14**: switch the hosted demo to DEMO mode. From this point the demo URL is permanent and stable.
- **Day 14 onward**: keep developing in LIVE mode locally; the deployed demo runs DEMO mode.
- **After June 7** (trial expires): we can no longer regenerate LIVE traces, but our deployed DEMO mode keeps serving the cached ones. Submit on June 9. Judging runs June 22 – July 6 against the DEMO-mode URL.

## Honesty in the demo

The 3-minute video will be recorded against LIVE mode (with the real Fivetran trial still active, ideally before June 7). The README will note that the *hosted demo URL serves a cached replay* of those LIVE runs, but the agent code in the repo is the same code that produced them, runnable end-to-end against any Fivetran account.

That framing is honest and judges-friendly. It's also a clean architecture pattern — the same code, just a different execution mode.
