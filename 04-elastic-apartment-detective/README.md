# Track 4: Elastic — Apartment Hunting Detective (one-pager)

> **This is a pivot backup, not a primary build.** If our main project hits a wall, this is the next-best target.

## One-liner
*"Zillow tells you a price. This agent tells you the truth."* — A semantic-search agent that researches an apartment listing across public data (HPD violations, recent Reddit/Yelp/Curbed mentions, court records, noise complaints, restaurant-noise reports) and gives the renter a brutal honesty report.

## Why Elastic
The data is all public and unstructured — exactly what Elastic's hybrid keyword + vector search exists for. Almost every search becomes "find me Reddit posts about X address that read like complaints, even if they don't say 'complaint.'" That's pure semantic search territory.

## Partner integration points
- **Elastic Agent Builder MCP server** (Kibana 9.2+) with custom tools:
  - `search_apartment_complaints` (vector + keyword over indexed Reddit/Yelp/Curbed/local-news)
  - `query_hpd_violations` (structured search over HPD JSON dataset)
  - `query_noise_complaints` (structured search over 311 NYC data, plus equivalents for SF, LA, etc.)
  - `find_nearby_restaurant_noise` (geo-bounded search over Yelp + 311 noise)
- ES|QL for the structured queries; semantic kNN for the vibe/complaint searches.

## Architecture (rough)
```
User submits listing URL (Zillow/StreetEasy/Apartments.com)
  → Cloud Function scrapes address + basic metadata
  → Agent Builder + Gemini 3 picks tools
     ├── search apartment-name + address in indexed Reddit
     ├── search building name in indexed Curbed/Streetsblog
     ├── query HPD violations DB
     ├── query 311 noise complaints
     └── search Yelp for nearby noise complaints
  → Agent synthesizes a "truth report" with risk score + flags
Output: PDF + dashboard with red flags highlighted
```

## Data we'd ingest into Elastic (Day 3–6)
- 5 years of Reddit r/AskNYC, r/sanfrancisco, r/AskLA, etc.
- Curbed + Streetsblog + The Real Deal articles
- NYC HPD Violations dataset (open data)
- 311 noise complaints (NYC, SF, LA — open data)
- Yelp reviews (with restaurant geo info)
- Court records (eviction filings, where public)

This is ~10 GB and the bulk of the work.

## Demo flow (3 min)
- 0:00–0:15: Hook — "Zillow won't tell you the building has 14 HPD violations. This agent will."
- 0:15–0:45: Paste a Zillow URL. Agent kicks off.
- 0:45–2:15: Reasoning streams as agent searches across 6 data sources. Real findings appear: "14 open HPD violations including lead paint", "3 Reddit threads about bedbugs in this building (2024, 2025)", "Restaurant downstairs has 47 noise complaints this year", "Building lost a tenant lawsuit for $42K in 2024."
- 2:15–2:45: Final report card. Risk score: 7.4/10. RED FLAGS: lead paint, noise.
- 2:45–3:00: Tagline + tech stack.

## Why this is our backup, not primary
- **Data ingestion is heavy** — we'd burn a week on it before the agent gets interesting
- **City-specific data limits the universal-pain story** (works great for NYC, weaker for smaller cities)
- **Partner is "merely" doing search** — not autonomously orchestrating systems like Fivetran in write mode

## When to pivot to this
- If GCP Agent Builder access is blocked but we have Elastic Cloud working (Elastic Agent Builder is GA)
- If we want a lighter scope (no SaaS sandboxes to set up — just ingest public data)

## Estimated build effort
- 4 days data ingestion + indexing
- 6 days agent + tools + UI
- 4 days polish + video + Devpost
- 3 days buffer

Comfortable in 17 days with focused work.

## Honest weakness
The Elastic Agent Builder MCP is relatively new (GA in Kibana 9.3) — fewer worked examples in the wild than the Fivetran or MongoDB MCPs. We'd be on the bleeding edge.
