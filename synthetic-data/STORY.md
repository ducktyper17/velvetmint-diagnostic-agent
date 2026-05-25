# Demo narrative — "VelvetMint"

The fake DTC brand the agent will diagnose. This document is the **ground truth** the agent must reach. If the demo is going right, the agent's final diagnosis matches this story almost exactly.

## The brand

- **Name**: VelvetMint
- **Category**: Premium skincare (cleansers, serums, moisturizers)
- **Founded**: March 2024
- **Founder**: "Maya Chen" (composite persona)
- **DTC channels**: Shopify (primary), Amazon (small)
- **AOV**: $54
- **Best seller**: "Mint Renewal Serum" ($38)

## Growth arc (so the data feels real)

| Period | Monthly revenue | Notes |
|---|---|---|
| Mar 2024 launch | $8K | Pre-launch press, friends and family |
| Q3 2024 | $25K | First viral TikTok |
| Q4 2024 | $80K | Black Friday + Q4 paid ramp |
| Q1 2025 | $120K | Consistent growth |
| Q2-Q3 2025 | $160K avg | Hit plateau |
| Q4 2025 | $210K | Q4 paid lift |
| Q1 2026 | $195K avg | Mild post-Q4 hangover |
| Apr 2026 | $200K | Normal |
| **May 2026** | **$156K projected (−22%)** | **The demo's "what's wrong?" moment** |

## The three ground-truth findings (what the agent must surface)

These are layered: any individual one could be coincidence, but together they explain the drop. The agent's value is in finding all three and quantifying them.

### Finding #1: TikTok creative is stale (∼$17K/mo loss)

- **Symptom**: TikTok Ads ROAS dropped from 2.4 (Apr) → 1.4 (May), −41%
- **Root cause**: Last new creative launched April 7, 2026 — 47 days ago. The same 3 video ads have been running on increasing budget since.
- **Quantification in the data**:
  - Frequency rose from 1.8 → 5.4 (same audiences seeing same ads 3x more)
  - CTR fell from 2.3% → 0.8%
  - CPM rose from $8 → $14 (Meta penalizes stale creative)
  - Spend held at $24K/mo but attributed revenue: $58K (Apr) → $34K (May)
- **Fix**: Launch 5+ new creative variations in week 1, kill the 3 dying ads

### Finding #2: Email list decay (∼$8K/mo loss)

- **Symptom**: Klaviyo abandoned-cart and welcome flows revenue dropped from $34K → $26K month-over-month
- **Root cause**: The Shopify popup that drives email captures broke on May 3, 2026, after the brand deployed a Shopify theme update. The popup JS errors silently. The team hasn't noticed because the rest of the site works.
- **Quantification in the data**:
  - Pre-May 3: ∼600 new signups/week
  - Post-May 3: ∼80 new signups/week (organic, checkout-only)
  - Open rate dropped 22% → 18% (list age skew)
  - List growth turned negative when accounting for unsubscribes
- **Fix**: A 30-minute Shopify theme rollback + a popup-monitoring sanity check

### Finding #3: iOS Safari checkout broken (∼$12K/mo loss)

- **Symptom**: Cart-to-checkout conversion looks stable in aggregate, but breaks out badly when sliced by browser
- **Root cause**: The same May 3 Shopify theme update introduced a JS error in a third-party payment widget on iOS Safari. iOS Safari = 32% of mobile traffic. The error rate on iOS Safari is 100%. Checkout completion on iOS Safari fell from 78% → 41%.
- **Quantification in the data**:
  - Chrome desktop: cart-to-checkout 81% → 80% (stable)
  - Chrome mobile: 75% → 73% (stable)
  - iOS Safari: 78% → 41% (broken)
  - Android Chrome: 71% → 70% (stable)
- **Fix**: Patch the payment widget for iOS Safari; the team can also add a browser-segmented funnel alert

## What "diagnosing" looks like in the agent's reasoning trace

The agent should produce reasoning visible to the user like:

> *"Maya asked why revenue is down 22% in May. Let me set up data sources..."*
>
> *"[Fivetran] Creating connector: Shopify → BigQuery... done."*
> *"[Fivetran] Creating connector: Klaviyo → BigQuery... done."*
> *"[Fivetran] Creating connector: Meta Ads → BigQuery... done."*
> *"[Fivetran] Creating connector: TikTok Ads → BigQuery... done."*
> *"[Fivetran] Creating connector: Google Ads → BigQuery... done."*
> *"[Fivetran] Creating connector: Stripe → BigQuery... done."*
> *"[Fivetran] Syncing last 90 days... 6/6 done in 47 seconds."*
>
> *"Hypothesis 1: Is paid spending efficiently? Querying Meta + Google + TikTok ROAS by channel..."*
> *"Found: TikTok ROAS dropped 41% in May. Drilling in."*
> *"Cause: No new creative launched in 47 days. CTR fell from 2.3% to 0.8%. Frequency capped audiences."*
>
> *"Hypothesis 2: Is the email channel healthy? Querying Klaviyo flows revenue + list growth..."*
> *"Found: New signups dropped 87% starting May 3. Existing flows revenue fell $8K MoM."*
> *"Cause: Probable Shopify popup malfunction starting May 3."*
>
> *"Hypothesis 3: Is the funnel converting normally? Querying cart→checkout by browser..."*
> *"Found: iOS Safari cart→checkout dropped 78% to 41%. Other browsers stable."*
> *"Cause: Probable JS error in checkout flow on iOS Safari, starting around May 3."*
>
> *"Summary diagnosis:*
> *   1. Stale TikTok creative → ~$17K/mo loss → ship 5 new ad variations*
> *   2. Broken email popup → ~$8K/mo loss → roll back Shopify theme*
> *   3. iOS Safari checkout JS error → ~$12K/mo loss → patch payment widget*
> *Total estimated impact: ~$37K/mo. Confirms ~80% of the 22% drop."*

That story arc — *three plausible hypotheses, each independently confirmed in data* — is what makes the demo feel like real diagnostic intelligence, not a chatbot summarizing.

## Why this story specifically

- **Multi-cause is harder than single-cause** — a one-bug demo would feel like "just an alert."
- **All three causes are common in real DTC** — stale ad creative, broken Shopify code after theme updates, browser-specific bugs. Judges with DTC experience will nod.
- **Each cause requires a different data source to detect**, which justifies the multi-source Fivetran story:
  - Stale TikTok → TikTok Ads + Meta Ads data
  - Broken popup → Klaviyo data (must correlate with Shopify deploy dates)
  - iOS Safari bug → Shopify checkout data segmented by browser
- **Quantifiable with money** — every finding has a dollar number, which lands hard in the video
