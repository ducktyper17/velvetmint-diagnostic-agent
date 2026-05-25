# Synthetic data for the VelvetMint demo

This folder contains 90 days of realistic-looking data for 6 SaaS sources, encoded with the three "ground truth" findings the agent must surface. See `STORY.md` for the narrative.

## Regenerate

```bash
python3 generate.py --seed 42
```

Pure stdlib. No deps. Deterministic given the same seed.

## Outputs

```
synthetic-data/
├── shopify/
│   ├── orders.ndjson        ~30K orders, 90 days
│   ├── checkouts.ndjson     ~45K checkout attempts (with browser breakdown)
│   └── customers.ndjson     ~20K customers
├── klaviyo/
│   ├── profiles.ndjson      ~6K email subscribers (with source: popup/checkout/organic)
│   ├── campaigns.ndjson     ~13 weekly newsletter sends
│   └── flows.ndjson         daily flow revenue (welcome / abandoned cart / post-purchase)
├── meta-ads/                stable performance (control)
├── google-ads/              stable performance (control)
├── tiktok-ads/
│   ├── ads.ndjson           3 active ads — all created on April 7 (the staleness)
│   └── insights.ndjson      daily frequency, CTR, CPM, ROAS — visibly degrading
├── stripe/                  ~9K charges + ~100 refunds
└── yotpo/                   ~800 product reviews (stable; helps the agent rule OUT a product-quality issue)
```

## Encoded ground truth

| Source | Signal | Why |
|---|---|---|
| Shopify checkouts | iOS Safari completion drops 78% → 41% after May 3 | Theme deploy broke payment widget on iOS Safari |
| Klaviyo profiles | New signups drop from ~85/day → ~11/day after May 3 | Same theme deploy broke the popup |
| Klaviyo flows | `welcome_series` revenue collapses after May 3 | No new signups to feed it |
| TikTok insights | Frequency rises 1.8 → 5.4, CTR falls 2.3% → 0.8%, ROAS 2.4 → 0.9 | No new creative since April 7 |
| Meta / Google Ads | Stable | Control. Tells the agent paid social is fine for non-TikTok channels |
| Yotpo | Stable 4.5★ avg | Control. Rules out a product issue |

## How the agent uses this

In the real run, Fivetran would ingest these sources into BigQuery. For the hackathon demo we can either:

1. **Real path**: Mount each NDJSON file in a fake "SaaS" via a tiny `mock-saas` server that mimics each API. Fivetran's connectors hit those endpoints. Most realistic.
2. **Faster path**: Pre-load BigQuery directly from these NDJSONs (skip Fivetran's read step), but use Fivetran MCP to *manage* (create/sync/configure) the connectors for the demo's "agent set up the pipelines" beat. Lighter on infra.

We'll likely use a hybrid in Week 2.

## Notes for diagnosis prompts

When tuning the system prompt, the agent should learn to:

1. Always check multiple sources before concluding
2. Quantify each finding in dollars
3. Look for **inflection dates** (changepoints), not just averages — the story is in *when* things changed, not just *what* averages are
4. Cross-reference timing — both Klaviyo signups AND iOS Safari checkout broke on the same day (May 3), which suggests a shared cause (the Shopify theme deploy)

That cross-reference is the agent's "aha moment" in the demo.
