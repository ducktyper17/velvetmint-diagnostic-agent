# Elastic Apartment Detective - Build Plan

## Goal
Ship an Elastic-track demo that feels polished, grounded, and obviously useful:

**paste a listing URL -> watch the agent investigate -> get a renter risk brief with evidence**

## Non-negotiables
- Gemini-powered agent on Google Cloud
- Elastic Agent Builder MCP integration
- At least one hybrid or semantic retrieval tool
- At least two ES|QL-backed tools
- Memory writeback into Elasticsearch
- Hosted demo URL
- Public repo + 3-minute video

## Ruthless scope
### In scope
- NYC only
- StreetEasy/Zillow listing input
- HPD violations
- NYC 311 complaints
- Curated Reddit/news corpus
- One clean renter brief page

### Out of scope
- Nationwide support
- Property-manager outreach automation
- Yelp, court records, or social scraping at scale
- Multi-user accounts
- PDF export

## System shape
### Frontend
- Simple listing input
- Streaming investigation state
- Final renter brief with citations

### Backend
- Listing parser / address normalizer
- Gemini orchestration loop
- Elastic MCP tool calls
- Brief synthesis + writeback to memory index

### Elastic
- `hpd_violations` index
- `nyc_311` index
- `tenant_signal_docs` index
- `building_briefs` memory index

## Tool list
### `search_building_memory`
Looks up prior analyses for the address or building.

### `get_hpd_violations`
Returns open violations, recency, and severity counts.

### `get_311_signals`
Returns complaint clusters by category and recent trend.

### `search_tenant_sentiment`
Hybrid search over Reddit/news chunks.

### `compare_to_neighborhood_baseline`
Compares complaint density to nearby addresses or ZIP baseline.

### `save_building_brief`
Stores extracted findings for reuse in follow-up questions.

## Suggested 7-day path
### Day 1
- Create Elastic Cloud Serverless project
- Enable Agent Builder
- get the MCP endpoint working from a Gemini-compatible client
- create empty target indices

### Day 2
- load HPD data
- load NYC 311 subset
- validate address fields, timestamps, and geo fields
- test first ES|QL queries manually

### Day 3
- create `get_hpd_violations`
- create `get_311_signals`
- add one comparison query for neighborhood baseline
- make sure the tools return small, model-friendly payloads

### Day 4
- ingest curated Reddit/news corpus
- create `search_tenant_sentiment`
- test hybrid retrieval on 3-5 demo addresses

### Day 5
- build listing parser and address normalization
- connect Gemini orchestration to Elastic MCP
- return a structured renter brief

### Day 6
- add `building_briefs` writeback
- support follow-up questions against stored memory
- polish tool descriptions so the model chooses them reliably

### Day 7
- tighten UI and loading states
- seed one perfect demo listing and one safe backup listing
- record the walkthrough

## Demo script target
### Scene 1
"This looks like a great apartment. Should I trust it?"

### Scene 2
Paste listing URL and stream tool activity.

### Scene 3
Show three concrete findings:
- recurring building issue
- neighborhood complaint trend
- unstructured text evidence

### Scene 4
Show final risk brief and recommended landlord questions.

### Scene 5
Ask one follow-up question to prove memory and grounded reasoning.

## Technical risks and mitigation
### Address normalization fails
Mitigation: normalize borough, ZIP, and street abbreviations; keep a seeded demo set.

### Retrieval is noisy
Mitigation: curate the text corpus and keep chunking simple; bias toward precision over coverage.

### Agent over-calls tools
Mitigation: keep tool descriptions narrow and output schemas compact.

### Demo data is weak
Mitigation: choose one address with obvious public signals and design the demo around it.

## Success bar
We should be able to demo all of this live:

1. user pastes a listing URL
2. agent runs at least 3 meaningful Elastic-backed tools
3. final answer includes hard evidence plus fuzzy warning signals
4. follow-up question works without rerunning the full investigation from scratch

If those 4 things work, this is a credible top-track Elastic submission.
