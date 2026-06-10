# Apartment Detective — Devpost draft

> Paste a rental listing. Get the truth before you sign. A Gemini-powered renter
> due-diligence agent that investigates a NYC listing across public housing
> records, 311 complaints, and tenant chatter — all grounded in Elastic — and
> returns an evidence-backed risk brief in under a minute.

## Inspiration

Apartment listings are conversion-optimized marketing. They show you the
renovated kitchen; they never show you the five open heat violations, the
late-night noise complaints, or the tenant thread about paper-thin walls. The
information that would actually change your decision is sitting in public
records and forum posts — scattered, messy, and impossible to assemble in the
ten minutes you have before someone else signs the lease.

We wanted an adversarial counterpart to the listing: an agent whose only job is
regret prevention. The Elastic track was the natural home for it. The core
motion — "combine exact facts with fuzzy warnings" — is exactly what Elastic is
built for: ES|QL tools over structured housing data, ELSER hybrid search over
unstructured tenant sentiment, and a write-back memory layer so the building
gets smarter every time someone investigates it. Nothing about this product
works without that retrieval layer, and Elastic gives us all of it through one
MCP integration.

## What it does

Apartment Detective is a Gemini-powered investigation agent that runs as a
service. You paste a StreetEasy or Zillow URL; it normalizes the address and:

1. Calls `search_building_memory` to check Elastic for a prior brief on the building.
2. Runs `get_hpd_violations` — an ES|QL tool over NYC HPD housing violations — for open count, severe categories, and recent examples.
3. Runs `get_311_signals` — an ES|QL tool over NYC 311 — for complaint volume, top categories, and the late-night noise share.
4. Runs `search_tenant_sentiment` — a **hybrid (ELSER semantic + keyword) search** over a curated Reddit/local-news corpus — to surface indirect complaints by meaning.
5. Runs `compare_to_neighborhood_baseline` — an ES|QL aggregation — to flag buildings that are materially worse than their ZIP.
6. Synthesizes a renter risk brief: a 0–10 score, top red flags, supporting evidence, and three questions to ask the landlord.
7. Calls `save_building_brief` to write the normalized brief back into the Elastic `building_briefs` index.

The whole investigation streams live to a Next.js dashboard over Server-Sent
Events, so you watch the agent think — every public thought, every tool call,
every result, all five reads fanned out in a single parallel batch.

The payoff is the follow-up. Ask "What's the biggest concern if I work nights?"
and the agent does **not** re-investigate — it reads its own saved brief back
from Elastic and answers from memory. That writeback is what turns a one-shot
report into a context layer.

## How we built it

Two services, demoable from a single laptop with no credentials.

**Agent (`agent/`)** is a FastAPI service exposing `/investigate` as SSE. The
investigation loop is a ReAct controller around **Gemini 2.5 Flash on Vertex
AI**, with forced function-calling mode and seven declared tools mapped to the
Elastic Agent Builder MCP surface. The key design choice: the model emits all
five read tools in one turn and we fan them out concurrently with
`asyncio.gather`, so the five Elastic calls run in parallel inside a single
Gemini turn — that's where the per-investigation latency lives. Flash over Pro
was deliberate: this is a tool-routing task, and the user feels per-turn latency
the moment they press Investigate.

**Elastic (`elastic/` + `agent/scripts/`)** is the heart of it. Four indices —
`hpd_violations`, `nyc_311`, `tenant_signal_docs`, `building_briefs` — provisioned
by `elastic_setup.py`. The tenant corpus uses a `semantic_text` field, so ELSER
runs automatically on ingest and query and powers the hybrid search. Real NYC
Open Data flows in via `ingest_nyc.py` (Socrata API, no token needed). The six
Agent Builder tools are documented as ES|QL in `elastic/agent_builder_tools.md`.

**Frontend (`frontend/`)** is a Next.js 14 dashboard: a paste-a-link header, an
evidence strip that derives a live risk dashboard from the streamed tool
results, a thinking panel, an Elastic tool timeline with `ES|QL` / `hybrid` /
`memory` badges, and the renter risk brief. The SSE stream is proxied through a
Next.js API route so the agent URL stays server-side.

**Demo + replay modes** were the best decisions we made. `DEMO_MODE` makes the
Elastic tools return seeded sample payloads; `STUB_GEMINI_RESPONSES` makes the
planner deterministic. Together they let the entire product run end-to-end with
no GCP or Elastic credentials, and `run_replay` adds human-readable pacing so the
on-stage demo is identical every time and cannot fail on connectivity. The whole
replay is real SSE through the real pipeline — only the model and Elastic calls
are stubbed.

## Challenges we ran into

- **Address normalization.** Listing URLs give you a slug, not a clean address. We normalize aggressively and, for the demo, snap a slug-derived address back to the canonical building so the brief reads "123 Orchard St, New York, NY 10002" instead of a title-cased slug. Seeded demo addresses guarantee the demo sings.
- **MCP result envelopes.** Agent Builder returns custom-tool output as a JSON string inside the MCP `content[]` channel (or `structuredContent`), not as raw JSON. We added `_normalize_mcp_result` to unwrap and parse it before the typed Pydantic wrappers read fields off it.
- **Keeping the agent from feeling like a report generator.** The fix was making the retrieval visible (streamed tool calls with retrieval-type badges) and making the memory writeback pay off in the follow-up question — so the agent demonstrably gets smarter on the second query.

## Accomplishments we're proud of

- Elastic is genuinely load-bearing: four ES|QL/aggregation tools, one ELSER hybrid search, and a write-back memory layer. Remove Elastic and the agent has no evidence, no semantic recall, and no memory.
- The five-reads-in-one-turn parallel fan-out is real concurrency, not a scripted sequence.
- The product runs with zero credentials for reviewers, and upgrades to fully live by flipping two flags.

## What we learned

The strongest partner integrations aren't the ones that call the most tools —
they're the ones where removing the partner collapses the product. Designing the
demo around "what does the listing hide?" forced every Elastic capability
(structured filters, hybrid retrieval, memory) into the critical path instead of
bolting them on.

## What's next

Multi-city support, address-level geo_distance filtering on 311, a richer tenant
corpus via the Agent Builder web connectors, and a Chrome extension that runs the
investigation inline on any listing page.

## Built with

Gemini 2.5 Flash · Vertex AI · Google Cloud Run · Elastic Cloud Serverless ·
Elastic Agent Builder MCP (ES|QL + ELSER hybrid search) · NYC Open Data (HPD +
311) · FastAPI · Next.js 14 · Server-Sent Events · Apache 2.0
