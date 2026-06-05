# Track 4: Elastic — Apartment Hunting Detective

## Positioning
This is the strongest Elastic-specific direction in the repo if we want a fast, judges-friendly build that makes the partner feel essential instead of decorative.

The old version was too broad: too many cities, too many sources, too much ingestion. The winning version is narrower and sharper.

## One-liner
*"Paste a listing. Get the truth before you sign."*  
An evidence-backed rental due-diligence agent that takes a StreetEasy or Zillow listing, searches public housing and neighborhood signals, and returns a renter risk brief with citations, red flags, and suggested questions to ask the landlord.

## Why this can win the Elastic track
This idea matches what Elastic is explicitly pushing in the hackathon resources:

- **Hybrid retrieval** over messy text and structured records
- **ES|QL tools** for fast filters, aggregations, and comparisons
- **Elastic as a context layer** so the agent writes back building summaries and gets smarter on repeat queries
- **Built-in MCP server** from Elastic Agent Builder, exposed directly to a Gemini agent on Google Cloud

This is not "search with a chatbot UI." Elastic is doing the hard part:

1. turning mixed public data into agent-usable tools,
2. retrieving the right evidence across structured and unstructured sources,
3. storing normalized building memory so the second query is faster and smarter.

## The better path
We should build **NYC-only MVP** first and optimize for one killer demo, not nationwide coverage.

### Scope cuts that make this viable
- **One city:** NYC only
- **One primary user flow:** paste listing URL -> get risk report
- **Four data sources in MVP:**
  - NYC HPD violations
  - NYC 311 complaints (noise, heat, pests, illegal dumping, etc.)
  - Curated Reddit/news corpus for tenant sentiment and anecdotes
  - Listing metadata extracted from StreetEasy/Zillow page
- **One memory layer:** a `building_briefs` index where the agent stores extracted facts, summaries, and prior findings

### Explicitly out for MVP
- Multi-city support
- Yelp ingestion
- Court-record integrations
- PDF generation
- Full autonomous browsing across the open web

Those can all exist as stretch goals, but they should not be on the critical path.

## Product story
Zillow tells renters what looks good. This agent tells them what could go wrong.

The output is not just a score. It answers:

- What building-level risks already show up in public records?
- Is this address in a recurring complaint hotspot?
- Are there strong text signals about pests, heat, management issues, or nightlife noise?
- What are the top 3 questions the renter should ask before applying?

That makes the agent useful, legible, and emotionally sticky in a 3-minute demo.

## Why Elastic is load-bearing
The core motion is: "combine exact facts with fuzzy warnings."

That is exactly where Elastic wins:

- **HPD + 311** need structured filters and aggregations -> ES|QL tools
- **Reddit/news sentiment** needs semantic and hybrid search -> Elastic search tools
- **Repeat usage** benefits from stored memory -> write summaries and extracted facts back into Elasticsearch
- **Follow-up questions** get better because the agent can search both raw evidence and prior synthesized briefs

Without Elastic, this becomes a brittle pile of scripts. With Elastic, it becomes one search-native context layer.

## Recommended architecture
```text
User pastes StreetEasy/Zillow URL
  -> Cloud Run listing parser extracts normalized address + listing metadata
  -> Gemini agent on Google Cloud Agent Builder or a code-owned backend calls Elastic MCP tools
     -> search_building_memory
     -> get_hpd_violations
     -> get_311_signals
     -> search_tenant_sentiment
     -> compare_to_neighborhood_baseline
  -> agent synthesizes a renter brief with citations
  -> save_building_brief writes the normalized summary back to Elastic
Output: renter risk report + supporting evidence + "questions to ask"
```

## MCP tool design
These are the tools that make the demo feel real:

### 1. `search_building_memory`
Checks whether we have already analyzed this building or address. Returns stored summaries, extracted red flags, and prior evidence links.

### 2. `get_hpd_violations`
ES|QL-backed tool over the HPD dataset. Returns open violations, recent severe issues, recurring categories, and counts by type.

### 3. `get_311_signals`
ES|QL-backed tool over NYC 311 complaints near the address. Supports time windows, radius filters, and category groupings.

### 4. `search_tenant_sentiment`
Hybrid search over curated Reddit and local-news chunks. Finds posts and articles that feel complaint-like even when the wording is indirect.

### 5. `compare_to_neighborhood_baseline`
Aggregates complaint density and category mix against nearby listings or ZIP-level baselines so we can say "this is materially worse than the local norm."

### 6. `save_building_brief`
Writes back a normalized building brief with risk factors, confidence, and evidence pointers. This is the context-layer move that makes Elastic feel advanced.

## Data plan
The old draft assumed massive ingestion. We do not need that.

### MVP ingestion
- **NYC HPD violations** for building-level hard evidence
- **NYC 311 complaints** for quality-of-life signals
- **Small curated Reddit/news corpus** for semantic search and emotional proof
- **Optional seed set of known demo addresses** so the demo is guaranteed to sing

This is enough to show hybrid search, ES|QL, memory, and grounded reporting without drowning in ETL.

## Demo flow (3 minutes)
### 0:00-0:20
Hook: "Apartment sites optimize for conversion. We optimize for regret prevention."

### 0:20-0:45
Paste a real listing URL. The agent extracts the address and explains what it is checking.

### 0:45-1:45
Tool calls stream:
- recurring heat complaints
- rodent or pest violations
- unusual neighborhood noise density
- complaint-like Reddit or local-news mentions

### 1:45-2:25
Final renter brief appears:
- overall risk score
- top red flags
- supporting evidence
- confidence level
- "questions to ask before you apply"

### 2:25-3:00
Follow-up question:
"Would you apply here if I work nights?" or "What is the single biggest concern?"

That follow-up is where the stored context and Elastic retrieval really shine.

## Judge-facing score thesis
### Technological implementation
Strong because Elastic MCP is doing real work across both hybrid retrieval and ES|QL tool calls, not just a single decorative search.

### Design
Strong because the UX is simple, emotional, and obvious in one screen: paste listing -> get truth report.

### Potential impact
Very strong because renters make expensive, stressful decisions with incomplete information. This is not a novelty use case.

### Quality of the idea
Strong because most real-estate tools are listing marketplaces, not adversarial due-diligence agents.

## Build sequence
See `04-elastic-apartment-detective/build-plan.md` for the execution path. The short version:

1. Stand up Elastic Serverless + Agent Builder
2. Load HPD + 311
3. Create the 5-6 MCP tools above
4. Build the listing parser and Gemini orchestration
5. Add memory writeback
6. Polish the renter brief UX around one unforgettable demo listing

## Honest risks
- **Address matching can be messy** -> normalize aggressively and seed known demo addresses
- **Too little text corpus weakens semantic wow-factor** -> curate a small but high-signal Reddit/news set early
- **Agent feels like a report generator** -> keep live tool streaming and follow-up Q&A in the demo
- **Elastic memory layer gets skipped** -> do not skip it; this is one of the best differentiators from the old version

## Bottom line
If we commit to Elastic, this should be treated as a **primary build with ruthless scope control**, not as a backup that tries to ingest the world.

The winning shape is:

**one city, one paste-a-link flow, four data sources, six good tools, one unforgettable renter-risk demo.**
