# Architecture — Doctor's Note Decoder

> Single-service FastAPI agent on Cloud Run, Gemini 3 for multimodal
> extraction and final synthesis, MongoDB Atlas as the knowledge base and
> personal vault, the official MongoDB MCP server as the retrieval
> surface, and Voyage AI for embeddings. Deliberately small and boring so
> that the medical-legal framing — not the infrastructure — is where the
> review effort goes.

## System diagram (text)

```
                      +-------------------------------+
                      |   Browser / minimal HTML UI   |
                      |  (upload PDF / image / text)  |
                      +---------------+---------------+
                                      |
                                      |  multipart POST /decode
                                      v
              +-----------------------+-----------------------+
              |   FastAPI service on Cloud Run (agent/)       |
              |                                               |
              |   main.py        ->  /decode endpoint         |
              |   extractor.py   ->  Gemini 3 multimodal      |
              |   retriever.py   ->  MCP -> $vectorSearch     |
              |   responder.py   ->  Gemini 3 synthesis       |
              |   prompts.py     ->  hard-baked disclaimers   |
              +-----+----------------+----------------+-------+
                    |                |                |
                    |                |                |
        Vertex AI   |     MongoDB    |       Voyage AI (embeddings,
        (Gemini 3)  |     MCP server |       via the MCP server's
                    |     (stdio /   |       auto-embedding on insert)
                    |      streamable|
                    |      HTTP)     |
                    v                v
              +-----------+    +-----------+
              | Vertex AI |    |  MongoDB  |
              |  Gemini 3 |    |   Atlas   |
              |  Pro      |    |  cluster  |
              +-----------+    +-----+-----+
                                     |
                          +----------+----------+----------------+
                          |          |          |                |
                       literature  guidelines forum_posts    user_vault
                       (PubMed)    (e.g. ATA, (de-identified) (per-user,
                                    ACR, ESMO) excerpts)      gated)
                          \_________ all in a single Atlas project,
                                     each with a Voyage-embedded
                                     vector index ______/
```

The MCP server is the only thing that talks to Atlas in production. The
agent process never opens a raw `MongoClient` against the cluster (we
keep `pymongo` in `pyproject.toml` because the seed script uses it for
the initial schema bootstrap, but the request path goes through MCP).
This is deliberate so the agent's data access is bounded by the MCP
tool surface and is therefore auditable.

## Collections

All under one Atlas database, `doctors_note`:

| Collection | What it holds | Vector field | Embedding model |
|---|---|---|---|
| `literature` | PubMed abstracts (title + abstract) | `embedding` | Voyage `voyage-3-large` (or `voyage-medical` if GA) |
| `guidelines` | Clinical guideline excerpts (ATA, ACR TIRADS, ESMO, NCCN, etc.) | `embedding` | same |
| `forum_posts` | De-identified, consent-cleared patient-forum excerpts | `embedding` | same |
| `user_vault` | A user's saved past explanations | `embedding` | same |

Each non-vault collection also stores structured fields used as
`$vectorSearch` pre-filters:

- `condition` (e.g. `thyroid_nodule`, `breast_mass`, `lung_nodule`)
- `severity_tier` (`low` / `moderate` / `high`, used to surface base-rate
  context rather than worst-case)
- `source` (`pubmed` / `ata_guideline` / `acr_tirads_2017` / `forum:reddit_thyroid`)
- `published_year`
- `language` (default `en`)

These pre-filters are critical: without them the vector search will
happily pull the most semantically similar abstract, which may be a 1998
case report from a different patient population.

## Indexes

Each vector-bearing collection has one Atlas Vector Search index:

```json
{
  "name": "vector_index",
  "type": "vectorSearch",
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "condition" },
    { "type": "filter", "path": "severity_tier" },
    { "type": "filter", "path": "source" },
    { "type": "filter", "path": "published_year" },
    { "type": "filter", "path": "language" }
  ]
}
```

`numDimensions` follows whichever Voyage model we end up using; this is
the only line that changes if we swap embedding models.

## Request flow (`POST /decode`)

```
1.  Client uploads report (PDF | image | text).
2.  extractor.extract(report) ->
       Gemini 3 multimodal call.
       Returns: ExtractedReport {
         raw_text, modality, body_site,
         entities: [ {name, value, units, qualifiers}, ... ],
         primary_condition, severity_tier_guess
       }
       Extraction is deliberately conservative; no interpretation.
3.  retriever.retrieve(extracted) ->
       Builds two aggregation pipelines (literature, forum_posts), each
       with $vectorSearch + $match filters keyed off
       extracted.primary_condition and extracted.severity_tier_guess.
       Sends them to the MongoDB MCP server's `aggregate` tool.
       Returns: RetrievalBundle { lit_hits, forum_hits, guideline_hits }
4.  responder.respond(extracted, bundle) ->
       Gemini 3 synthesis call with prompts.SYSTEM_PROMPT.
       Returns: DecodedReport (Pydantic), which always contains:
         - translation
         - what_this_means
         - statistical_context
         - questions_to_ask          (exactly 3)
         - likely_followup           (yes/no + timeline)
         - disclaimer                (verbatim from LEGAL-DISCLAIMER.md)
         - sources                   (list of {source, title, url})
5.  Server returns the validated JSON to the client.
6.  (Optional) If user asks to save, we call MCP `insert-many` against
    user_vault with a per-user partition key.
```

If any step fails, the response is replaced with a soft fallback that
includes the disclaimer and a suggestion to talk to the clinician.
We never return a partial decoding without the disclaimer block.

## Why hybrid retrieval, specifically

A purely semantic search will collapse important distinctions (a forum
post about "thyroid cancer" looks neighbor-ish to a benign-nodule
abstract in embedding space). A purely structured filter cannot find
"papers about indeterminate nodules with a follow-up recommendation in
12 months" because that phrasing varies per paper.

So:

- `$vectorSearch` does semantic recall.
- `$match` pre-filters constrain by `condition`, `severity_tier`, and
  `published_year >= 2018` (recency).
- We then optionally re-rank by `score * recency_weight` so we don't
  surface a 2003 paper when a 2024 one with the same content exists.

All three live inside one MongoDB aggregation pipeline, which is the
clean way to express it.

## Why the official MongoDB MCP server, not a hand-rolled client

The hackathon explicitly rewards "agent uses tools to do the job," and
the MongoDB MCP server is the supported, documented tool surface for
Atlas operations from an agent. Going through it gives us:

- `find`, `aggregate` (with `$vectorSearch`), `count`,
  `collection-schema`, `collection-indexes`, `create-index`,
  `insert-many`, plus Atlas management tools (`atlas-create-free-cluster`,
  `atlas-list-projects`) when Atlas creds are set.
- Voyage AI auto-embedding on `insert-many` when `VOYAGE_API_KEY` is
  present — meaning we never have to maintain our own embedding pipeline
  for ingestion.
- A clean auditable boundary: every Atlas operation the agent performs
  is one of a fixed set of MCP tool calls. That is useful for both
  reasoning and for the legal/compliance posture.

## Deployment

| Component | Where |
|---|---|
| FastAPI service (`agent/`) | Cloud Run, single container, 1 CPU / 2 GiB |
| MongoDB MCP server | Sidecar in the same Cloud Run service, started by `main.py` startup hook (stdio transport) |
| Vertex AI calls | Direct from the service using the GCP project's default service account |
| Atlas cluster | M0 free tier in the same GCP region as Cloud Run, peered via PrivateLink in production (public allowlist for the demo) |
| Secrets | `MONGODB_URI`, `VOYAGE_API_KEY` in Secret Manager |

For the demo we run everything in `us-central1`.

## What is intentionally out of scope (backup scaffold)

- Full auth / user accounts. The vault collection is single-user for
  the demo and gated by a static demo token.
- A polished frontend. The demo uses a minimal upload form.
- HIPAA-grade compliance. We document the gap explicitly in
  `LEGAL-DISCLAIMER.md`. Real productization would be a separate effort
  with a BAA in place with both Google Cloud and MongoDB.
- Multi-language support. English only in the demo; the architecture
  has a `language` filter so adding more is mechanical, not structural.
