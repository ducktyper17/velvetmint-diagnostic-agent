# Demo script — 3-minute video

**Target length:** 2:55 (a buffer under the 3:00 cap).
**Voice:** clear narrator, founder-perspective. No music until the closer beat.
**Resolution:** 1080p, 60fps. Browser at 1440px, scaled so dashboard text is legible.
**Brand:** *VelvetMint*, fictional skincare DTC. Logo and product images live in
`frontend/public/demo-assets/`.

The script is broken into 12 fifteen-second beats. Each beat lists what the camera
shows, what the on-screen agent says (when relevant), and the narrator voiceover.

---

## Beat 1 — 0:00 to 0:15  Hook

**Camera:** Tight on a laptop screen. Slack notification flashes "Shopify daily
summary: revenue down 22% MoM." Cut to a panicked-looking founder closing the
notification.

**Narrator (VO):** *"Every DTC founder has had this morning. Revenue is down. You
have six tools that each tell a piece of the story, and zero that connect them."*

**Agent says:** (silent, agent not yet active)

---

## Beat 2 — 0:15 to 0:30  Set the question

**Camera:** Cut to the VelvetMint dashboard at `/dashboard`. Maya types into the
chat:

> "Why is my revenue down 22% this month?"

She hits send. The agent reasoning panel slides open on the right.

**Narrator (VO):** *"Meet Maya. Founder of VelvetMint, a skincare brand. She just
asked our agent the question every founder dreads."*

---

## Beat 3 — 0:30 to 0:45  Agent inventories the stack

**Camera:** Agent reasoning panel streams, line by line:

```
Plan: I need data from every source that influences revenue.
Checking which Fivetran connectors VelvetMint already has...
[tool] list_connections
  -> 0 connectors found
Need to set up: shopify, klaviyo, meta_ads, google_ads,
                tiktok_ads, stripe, yotpo
```

**Narrator (VO):** *"The agent looks at what data pipelines exist. There are none.
So it builds them."*

---

## Beat 4 — 0:45 to 1:00  Wires up Shopify + Klaviyo

**Camera:** Reasoning panel scrolls fast:

```
[tool] create_connection(source="shopify",
                         destination="bigquery_velvetmint")
  -> connection_id "ace_shopify_001" created
[tool] run_connection_setup_tests(connection_id="ace_shopify_001")
  -> all tests pass
[tool] sync_connection(connection_id="ace_shopify_001")
  -> sync started, 12 tables, ETA 4 min

[tool] create_connection(source="klaviyo", ...)
  -> connection_id "ace_klaviyo_001" created
  -> sync started
```

A small "connectors created" counter ticks: 1, 2.

**Narrator (VO):** *"It calls Fivetran's MCP server in write mode — `create_connection`,
`run_connection_setup_tests`, `sync_connection`. These are real Fivetran API
calls."*

---

## Beat 5 — 1:00 to 1:15  Wires up the rest

**Camera:** The counter ticks rapidly: 3, 4, 5, 6, 7. Sources show: Meta Ads,
Google Ads, TikTok Ads, Stripe, Yotpo. The `[tool]` lines blur with speed.

A horizontal bar at the top fills as syncs complete: ▓▓▓▓▓▓▓░ → ▓▓▓▓▓▓▓▓.

**Narrator (VO):** *"Seven connectors, 90 days of historical data, in under a
minute. The agent waits for the syncs to land in BigQuery."*

---

## Beat 6 — 1:15 to 1:30  Cross-references

**Camera:** Reasoning panel:

```
All 7 syncs complete. Running diagnostic battery...
[tool] query_synced_data(metric="roas_by_channel", window=90d)
[tool] query_synced_data(metric="email_engagement_decay", window=90d)
[tool] query_synced_data(metric="funnel_conv_by_browser", window=30d)
[tool] query_synced_data(metric="refund_rate", window=30d)
[tool] query_synced_data(metric="creative_fatigue_by_ad", window=30d)
[tool] query_synced_data(metric="paid_vs_organic_mix", window=90d)
... 12 checks
```

**Narrator (VO):** *"Now the analytical layer kicks in. ROAS by channel. List
decay. Funnel conversion by browser. Twelve diagnostic queries against the
unified data."*

---

## Beat 7 — 1:30 to 1:45  Cross-references — finding signal

**Camera:** Reasoning panel:

```
Anomaly detected: TikTok ROAS dropped 41% (May 2 onward)
Anomaly detected: email open rate dropped 18% (May 3 onward)
Anomaly detected: iOS Safari cart conversion dropped 22% (May 8 onward)
Three anomalies converge to explain a 22% revenue gap. Building report...
```

The reasoning panel collapses to a small chip. The main panel begins to render
the final report.

**Narrator (VO):** *"Three independent anomalies. Together they explain the
revenue gap exactly."*

---

## Beat 8 — 1:45 to 2:00  Finding 1 — TikTok creative fatigue

**Camera:** A clean shadcn/ui Card slides in:

> **Finding 1 — Paid acquisition**
> TikTok ROAS dropped 41% on May 2.
> **Cause:** Top 3 ad creatives are 47 days old. CTR fell from 2.1% to 0.7%.
> **Revenue impact:** $19,400 / month
> **Fix:** Pause the 3 fatigued creatives. Launch 2 new creative variants.
> Expected lift: +$12K–$18K MoM.

A small chart shows ROAS by week, with a sharp drop at May 2.

**Narrator (VO):** *"Finding 1: paid acquisition. The TikTok creatives went stale.
That's a $19K hit, with a fix."*

---

## Beat 9 — 2:00 to 2:15  Finding 2 — Email list decay

**Camera:** Card 2 slides in below Card 1:

> **Finding 2 — Retention**
> Email open rate dropped 18% on May 3.
> **Cause:** Welcome flow popup broken on the mobile homepage (Klaviyo signup
> events fell from 312/day to 41/day).
> **Revenue impact:** $11,200 / month (lifetime value of lost subscribers).
> **Fix:** Repair the popup; backfill the bounced subscribers from Shopify
> checkout emails.

**Narrator (VO):** *"Finding 2: retention. The signup popup broke on mobile.
The list stopped growing. That's $11K."*

---

## Beat 10 — 2:15 to 2:30  Finding 3 — Funnel conversion

**Camera:** Card 3 slides in:

> **Finding 3 — Conversion**
> iOS Safari checkout conversion dropped 22% on May 8.
> **Cause:** Checkout JS error introduced in Shopify theme commit
> `velvetmint-theme/commit/7b3aa1c` (deployed May 8). Error fires on
> `Apple Pay` button render for iOS 17.4+.
> **Revenue impact:** $7,800 / month
> **Fix:** Roll back the theme deploy. Or wrap the Apple Pay handler in
> a try/catch.

**Narrator (VO):** *"Finding 3: conversion. A theme deploy broke checkout on iOS
Safari. That's $7,800. Total: $38,400 of the $44,000 revenue gap, accounted for."*

---

## Beat 11 — 2:30 to 2:45  Tag the differentiator

**Camera:** Cut to a clean slide:

> **What just happened.**
> 1. The agent built 7 Fivetran data pipelines on its own.
> 2. It ran 12 cross-platform diagnostic queries.
> 3. It explained 87% of the revenue gap, with dollar amounts and fixes.
>
> **Tools used:** Google Cloud Agent Builder, Gemini 3, Fivetran MCP server
> (write mode), BigQuery, MongoDB Atlas, Cloud Run.

**Narrator (VO):** *"Three things made this possible: Google Cloud Agent Builder
orchestrating, Gemini 3 reasoning, and the Fivetran MCP server creating
connectors autonomously."*

---

## Beat 12 — 2:45 to 2:55  Closer + GitHub

**Camera:** Quick cut to the GitHub repo page (open-source, Apache-2.0 visible).
Then end card:

> **DTC Brand Health Diagnostic Agent**
> github.com/[your-handle]/dtc-diagnostic-agent
> Built for the Google Cloud Rapid Agent Hackathon, June 2026.

Fade to black.

**Narrator (VO):** *"Open source. Built in 19 days. The first agent that
diagnoses your DTC business across every channel — in 90 seconds."*

---

## Production checklist

- [ ] Pre-record reasoning trace from a real agent run, edit for tightness
- [ ] Pre-warm BigQuery with the seeded VelvetMint dataset
- [ ] Pre-create the 7 Fivetran connections so live `create_connection` is fast
      (or, on demo day, scripted to look fast — see `SCAFFOLD-NOTES.md`)
- [ ] Cursor / focus indicator visible whenever Maya types
- [ ] No real personal info on screen; all data is synthetic
- [ ] Audio: -16 LUFS integrated, narrator only
- [ ] Captions burned in for accessibility
- [ ] First frame is a still that previews the moment-of-truth (good thumbnail)
- [ ] Dry-run the full script end-to-end at least 5 times before recording

## Plan B — if connectors do not stream fast enough on demo day

Pre-record the connector-creation segment (beats 3-5), then continue live from
beat 6 with the synced data already in BigQuery. Disclose this in the Devpost
writeup ("connector setup pre-recorded for video pacing; full reasoning and
diagnosis run live"). The judges value the *quality* of the reasoning more than
the wall-clock realism.
