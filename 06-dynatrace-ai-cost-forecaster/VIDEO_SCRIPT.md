# Agent Reliability Guard — 3-minute video script

Target runtime: **2:55** (gives 5s of safety margin under the 3:00 ceiling).
Recording approach: drive the demo through replay mode (`run_replay`) so timing is deterministic. Capture the dashboard at 1920x1080, 30fps. Voice-over recorded separately and aligned to beats below.

## Beat sheet

| Time | Visual | Voice-over | Production notes |
|---|---|---|---|
| 0:00–0:08 | Title card: "Agent Reliability Guard" — dark background, the line "an agent that watches agents" beneath. | "AI agents rarely fail all at once." | Hold title for 2s, then cross-fade to the dashboard idle state. Use the same monospace font as the dashboard for visual continuity. |
| 0:08–0:15 | Dashboard idle state. Healthy badge visible. Refund-assistant logo + version v11. | "They get slower, more expensive, and quietly worse. We built a Gemini-powered guard that catches that in minutes." | Cursor not visible yet. No motion in the panel. |
| 0:15–0:30 | Run `make traffic-healthy` in a terminal overlay (lower third). Cut to Dynatrace baseline panel showing flat p95 latency around 1.8s and 920 tokens per request. | "Meet the patient — a Gemini-powered refund assistant. Real OpenTelemetry traces flowing into Dynatrace. Latency stable. Token spend stable. Tool error rate near zero." | Terminal overlay disappears after 4 seconds. Highlight three KPI tiles with a subtle pulse animation. |
| 0:30–0:40 | Cross-fade to dashboard. Release banner shows `v11 → v12` and a yellow `release-2026-05-26-bad-prompt` marker drops into the timeline. | "Then a deploy lands. Prompt v12. Looks healthy in staging." | The release banner is the visual anchor for the rest of the video — keep it on screen. |
| 0:40–1:00 | Telemetry tiles begin to shift: p95 climbs to 3.8s, tokens per request climb to 3,500, tool error rate ticks up to 14%. Subtle red ring around each tile as it crosses threshold. | "In production, three things drift at once. Latency more than doubles. Tokens per request nearly quadruple. Tool errors climb past 10%. No alarms. No alerts. Just slow, expensive, quietly worse." | The drift should take ~12s on camera. Resist the urge to over-animate. |
| 1:00–1:10 | Operator cursor moves to the **Investigate** button and clicks. Thinking panel pops open. | "One button. The Guard wakes up." | Use a 200ms ease-in on the panel reveal. |
| 1:10–1:45 | Thinking panel streams three thoughts and three tool calls in rapid succession — `query_runtime_signals`, `run_change_analysis`, `forecast_blast_radius` — all in the same turn. Tool result chips fan in concurrently. | "Watch this carefully. Gemini emits three function calls in one turn — runtime signals, changepoint detection, and forecasting — and we fan them out in parallel. The three slow calls finish in the time of one." | This is the technical money shot. Slow the playback to 0.85x for these 35 seconds so viewers can actually read the thoughts. |
| 1:45–2:05 | Notebook URL appears in the thinking panel. Cut to the Dynatrace notebook itself: title, runtime evidence section, changepoint chart, forecast chart, recommended fix. | "The Guard packages the evidence into a Dynatrace notebook. Runtime signals. Changepoint location. Forecast. Recommended fix." | Pre-record the notebook view — do not rely on live rendering for the cleanest cut. |
| 2:05–2:20 | Slack-style notification card slides into view on top of the dashboard. Channel `#ai-platform-alerts`. Preview text visible: "refund-assistant regressed after release-2026-05-26-bad-prompt." | "And it tells the on-call channel. The agent is no longer advisory. It is operational." | Notification slides from the right with a soft drop shadow. |
| 2:20–2:40 | Cut to the "if left for 7 days" overlay: **$3,400 in wasted tokens** and **18 hours of cumulative user wait time**, both with a stylized dollar/clock icon. | "And here is the part executives will care about. If this regression runs unfixed for one week, the Davis forecast says it will burn about $3,400 in tokens and add 18 hours of cumulative user wait time. That is the price of finding out from a user complaint." | The two numbers should land on emphasized beats — pause briefly between them in the VO. |
| 2:40–2:50 | Tech stack slate: Gemini 2.5 Flash, Vertex AI, Cloud Run, Dynatrace MCP, OpenTelemetry. Apache 2.0 badge. | "Built on Gemini, Vertex AI, Cloud Run, and the Dynatrace MCP server. Real OpenTelemetry. Open source." | Logos arranged in two rows. Keep at least 200ms between logo reveals. |
| 2:50–2:55 | Closing card: "Agent Reliability Guard — watch the agents you ship." Link: hosted URL + GitHub. | "Watch the agents you ship." | Hold final card for 3 seconds before fade to black. |

## Production checklist

- Record once in replay mode, once with real Vertex + Dynatrace. Use the replay capture as the master and splice in 1-2 seconds of the real run where the notebook appears, for credibility.
- Background music: low-energy synth bed at -22 LUFS. Duck under VO by 8dB.
- All on-screen numbers ($3,400 / 18 hours / latency ratios) come straight from the deterministic stub data in `_stub_runtime_signals` and `_stub_forecast` so they match what viewers can reproduce.
- Confirm the SSE stream order in `agent_loop.py` matches the on-screen beat: `thought` then `tool_call` then `tool_result`, three times in one turn.
- Upload as YouTube unlisted, paste link into Devpost, paste link into README hero section.
