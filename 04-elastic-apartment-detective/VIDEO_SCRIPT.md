# Apartment Detective — 3-minute video script

Target runtime: **2:55** (5s of safety margin under the 3:00 ceiling).
Recording approach: drive the demo through **replay mode** (`replay: true` on
`/investigate`, or the replay toggle) so the timing is deterministic. Capture the
dashboard at 1920x1080, 30fps. Voice-over recorded separately and aligned to the
beats below.

## Beat sheet

| Time | Visual | Voice-over | Production notes |
|---|---|---|---|
| 0:00–0:08 | Title card: "Apartment Detective" on dark background, line beneath: "Paste a listing. Get the truth before you sign." | "Apartment listings are written to make you sign." | Hold title 2s, cross-fade to the dashboard idle state in the same monospace font. |
| 0:08–0:18 | Dashboard idle. The listing URL field holds a real-looking StreetEasy link for 123 Orchard St. | "They show you the granite counters. They don't show you the public record. We built a Gemini agent that does — grounded entirely in Elastic." | Cursor not visible yet. No motion in the panel. |
| 0:18–0:28 | Cursor moves to **Investigate** and clicks. The live investigation panel opens, first thought streams in. | "Paste a link. The detective goes to work." | 200ms ease-in on the panel reveal. |
| 0:28–1:05 | Investigation panel streams one plan thought, then **five tool calls in a single turn** — `search_building_memory`, `get_hpd_violations`, `get_311_signals`, `search_tenant_sentiment`, `compare_to_neighborhood_baseline` — with the `ES|QL` / `hybrid` / `memory` badges visible. Result chips fan in concurrently. | "Five Elastic tools, one turn, run in parallel. Building memory. HPD housing violations over ES|QL. Three-eleven complaints. A hybrid semantic search over tenant chatter. And a comparison against the whole neighborhood." | The technical money shot. Slow playback to 0.85x here so viewers can read the badges and results. Let the evidence strip tiles light up red as they cross thresholds. |
| 1:05–1:20 | The evidence strip is fully populated: **5 open HPD violations**, **18 complaints/90d**, **61% late-night noise**, **1.7× vs neighborhood** — the bad tiles ringed in red/amber. | "And here's what the listing never told you. Five open housing violations. Eighteen complaints in ninety days. Sixty-one percent of nearby noise is after midnight. Almost twice the neighborhood norm." | Numbers land on emphasized VO beats; pause briefly between them. |
| 1:20–1:35 | Hybrid-search highlight: zoom the `search_tenant_sentiment` result line — "Tenant thread describes thin walls and bar noise after midnight." | "This one matters. We never searched for 'noise.' Elastic's semantic search surfaced a tenant complaining about 'thin walls and a bar two doors down' — by meaning, not keywords." | This is the Elastic-is-load-bearing proof. Hold the highlight 3s. |
| 1:35–1:58 | The renter risk brief card animates in: **9.8 / 10**, a **high-confidence** chip, top red flags, supporting evidence, three questions to ask. | "The detective writes a renter risk brief. Nine-point-eight out of ten — and high confidence, because five independent public sources all corroborate. The score says how bad. The confidence says how sure — and it's computed from the evidence, never guessed by the model." | Pre-frame the score dial filling to 9.8; let the green "high confidence" chip pop in 300ms after the dial. Keep the brief on screen. |
| 1:58–2:10 | Footer of the brief flashes: "Brief written back to the Elastic building_briefs index." | "And it writes that brief back into Elastic — so the building gets a memory." | Subtle highlight pulse on the `building_briefs` footer line. |
| 2:10–2:35 | Cut to the follow-up box. Type "What's the biggest concern if I work nights?" and submit. A fast answer streams, reusing the saved brief (memory hit shown). | "Now watch the payoff. 'What's the biggest concern if I work nights?' The agent doesn't re-investigate — it reads its own saved brief from Elastic and goes straight to the late-night noise. That's the context layer." | Show `search_building_memory` returning `found: true` this time. This proves the memory writeback closes the loop. |
| 2:35–2:48 | Tech stack slate: Gemini 2.5 Flash, Vertex AI, Cloud Run, Elastic Agent Builder MCP (ES|QL + ELSER hybrid), NYC Open Data. Apache 2.0 badge. | "Built on Gemini, Vertex AI, and Cloud Run, grounded in Elastic — ES|QL tools, ELSER hybrid search, and a write-back memory layer. Real NYC public data. Open source." | Logos in two rows, 200ms between reveals. |
| 2:48–2:55 | Closing card: "Apartment Detective — get the truth before you sign." Link: hosted URL + GitHub. | "Get the truth before you sign." | Hold final card 3s, fade to black. |

## Production checklist

- Record once in replay mode, once with the real Gemini + Elastic path. Use the replay capture as the master; splice 1–2s of the real run (the live ES|QL tool result) in around 1:00 for credibility.
- Every on-screen number (5 violations / 18 complaints / 61% / 1.7× / 9.8) comes straight from the seeded demo payload in `tools.py::_sample_payload`, so viewers can reproduce it.
- Confirm the SSE order in `agent_loop.py` matches the beats: one `thought`, then five `tool_call`s in iteration 1, then five `tool_result`s, then `save_building_brief`, then `final_report`.
- Background music: low-energy synth bed at -22 LUFS, ducked 8dB under VO.
- Upload as YouTube unlisted; paste the link into Devpost and the README hero.
