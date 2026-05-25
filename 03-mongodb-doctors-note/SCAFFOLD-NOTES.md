# Scaffold notes — Doctor's Note Decoder (backup)

> What is real, what is stubbed, what we have not started, how long the
> remaining work is, and where the project could break. This is a
> backup-tier scaffold — roughly 60% of the depth we'd put into the
> primary Fivetran submission. The primary lives in
> `../01-fivetran-dtc-diagnostic/`.

Last updated: 2026-05-23.

## What is complete

- **Project framing**: `README.md`, `architecture.md`, `demo-script.md`,
  `LEGAL-DISCLAIMER.md` are written end-to-end. The disclaimer file is
  the canonical source of truth and is loaded by `agent/prompts.py` at
  import time; the prompt cannot drift from the legal text.
- **Repository layout**: agent module skeleton in `agent/` with a flat
  Python layout (no `src/` subdir — keeps imports simple for a small
  service).
- **Response contract**: `responder.py` defines `DecodedReport` with
  Pydantic validators that enforce the two product invariants we care
  about most (non-empty disclaimer; follow-up text must reference the
  clinician). If the model fails to comply, validation fails and the
  client gets a 500 — by design.
- **Hybrid-retrieval pipeline builder**: `retriever.build_pipeline()`
  is real, pure, and unit-testable. It constructs a single
  `$vectorSearch` aggregation with structured pre-filters
  (`condition`, `severity_tier`, `published_year`, `language`) so
  retrieval will work correctly the moment the MCP call is wired in.
- **Seed script**: `seed_data.py` upserts sample literature, guideline,
  and (clearly fabricated) forum docs, plus creates the Atlas Vector
  Search index per collection. Idempotent on `_id`.
- **System prompts**: `prompts.py` contains the extraction and
  synthesis prompts with the framing rules from the legal doc
  hard-baked in. Few-shot examples are present but minimal.
- **Pinned dependencies**: `pyproject.toml` uses real package names
  with conservative minimum versions; anything we're not 100% sure
  about at the time of writing is marked `TODO confirm` rather than
  guessed.
- **Env contract**: `.env.example` covers MongoDB, MCP, Voyage, Vertex,
  and runtime knobs. `REQUIRE_DISCLAIMER_FILE` defaults on.

## What is stubbed

- **Gemini 3 extraction call** (`extractor._gemini_extract`). The
  function signature, schema, and prompt-loading are real; the actual
  Vertex AI call is a TODO. The stub returns a fixed thyroid example
  so the rest of the pipeline is end-to-end runnable.
- **Gemini 3 synthesis call** (`responder.respond`). Same pattern —
  schema, validators, and prompt are real; the model call is a TODO.
  The stub returns a complete, validation-passing `DecodedReport`.
- **MongoDB MCP session** (`main.py` lifespan + `retriever.retrieve`).
  The MCP server subprocess is not yet launched. The pipeline builder
  runs and produces correct aggregations; the dispatch to
  `session.call_tool("aggregate", ...)` is a TODO with the exact call
  shape commented inline.
- **Voyage auto-embedding**. We rely on the MongoDB MCP server's
  documented behavior: when `VOYAGE_API_KEY` is configured on the MCP
  server, `insert-many` auto-embeds text fields. The seed script
  intentionally inserts via raw pymongo (schema bootstrap path); the
  request-path inserts in `/vault/save` are stubbed and will use MCP
  once wired.
- **`/vault/save` endpoint**. Returns a stub response. No real auth.
- **Frontend**. None. The demo uses curl for now; a minimal upload
  page is post-pivot work.
- **Tests**. None. The component seams (extractor / retriever /
  responder as pure-ish functions with explicit schemas) make this
  easy to add later.

## Estimated work to demo-able

Assuming one engineer, working contiguous hours, GCP and Atlas projects
already provisioned with billing on:

| Block | Hours |
|---|---|
| Wire `extractor._gemini_extract` to Vertex AI (`google-cloud-aiplatform`), include real PDF/image path tests | 3 |
| Wire MCP subprocess in `main.lifespan` (start, healthcheck, teardown); add a thin wrapper around `session.call_tool("aggregate", ...)` | 4 |
| Wire `responder.respond` to Vertex AI with structured output (`response_schema=DecodedReport`), include the "soft fallback with disclaimer attached" branch on validation failure | 3 |
| Seed a real-feeling knowledge base: ~30 PubMed-style abstracts across 4 conditions, ~6 guideline excerpts, ~10 forum-shaped fabricated entries (all clearly labeled), verify Voyage embeddings populate via MCP `insert-many` | 4 |
| Minimal HTML upload page + result card; copy from the demo script | 2 |
| Cloud Run deploy + Secret Manager wiring + smoke test against Atlas | 3 |
| Demo video recording, editing, captions, disclaimer overlay | 4 |
| Buffer (you will lose at least this much to Vertex quotas, Atlas index propagation latency, and MCP version drift) | 3 |
| **Total** | **~26 hours** |

This is consistent with a 3-day sprint for one person, or one long
weekend for two people splitting on agent vs. demo polish.

## Top 3 risks

### 1. Legal / medical framing risk (the one we cannot ship through)

This is the risk that decides whether this project is submittable at
all, not how it ranks. A medical-information product that misframes
itself as diagnostic is not just a UX issue; it is a patient-safety
issue and a regulatory one. Specific failure modes:

- The model says "you have…" or "the diagnosis is…" in the
  `translation` or `what_this_means` fields. The system prompt forbids
  this and the disclaimer validator catches missing disclaimers, but
  we do not yet have a regex or LLM-judge gate that catches drift
  inside the prose. **Mitigation before demo:** add a post-generation
  rule check in `responder.respond` (regex match against a small
  banned-phrase list; on hit, regenerate with a stricter instruction
  or return a soft refusal).
- The disclaimer is technically present but visually skimmable; the
  judges (or anyone re-uploading the video) read only the hero card.
  **Mitigation:** the demo-script keeps the lower-third disclaimer
  band on for the entire video, and the response card UI prints the
  short disclaimer above the fold and links to the long one.
- The demo footage shows realistic patient data. **Mitigation:** the
  sample report PDF carries an explicit `SAMPLE — NOT A REAL PATIENT`
  marker and uses obviously fake identifiers; the seed forum data is
  labeled `source: "sample:fabricated"`.
- Devpost or a partner reposts the demo without the disclaimer band.
  **Mitigation:** the disclaimer is burned into the export, not
  overlaid by the player.

We should not pivot to this project unless we are willing to commit a
specific person to owning the framing review end-to-end.

### 2. MCP server runtime risk

The official MongoDB MCP server is young (relative to the MongoDB
driver itself). The risks we are watching:

- Version skew between what the docs describe and what is on npm at
  build time. `MCP_SERVER_CMD=npx -y mongodb-mcp-server …` always
  pulls latest, which is fine for the demo but unsafe for production.
  **Mitigation for the demo:** pin to a specific tag in the Cloud Run
  Dockerfile.
- Auto-embedding via Voyage in `insert-many` is configured server-side,
  not in our code. If the env or the server flags are wrong, ingestion
  succeeds without embeddings and vector search silently returns
  nothing. **Mitigation:** the seed script prints a loud reminder; we
  should add an end-of-seed assertion that at least one document has
  a non-null `embedding`.
- Streamable HTTP vs. stdio transport: we have planned for stdio
  inside a Cloud Run container. If we end up needing HTTP transport
  for any reason (e.g. to share the MCP server across services),
  `main.lifespan` has to change.

### 3. Track-competition risk

MongoDB is a mid-crowded track (per `../DECISION.md`, est. 300–500
submissions; lower than GitLab, higher than Fivetran and Arize). Many
of those submissions will be "RAG over my docs in Atlas." Doctor's
Note Decoder differentiates on:

- **Hybrid retrieval inside one aggregation pipeline**, not a
  hand-stitched ANN + filter combo.
- **Domain framing**, which is also the legal risk above. Most
  competitors will not have a `LEGAL-DISCLAIMER.md` file at all.
- **Auto-embedding via MCP**, not a separate embedding service.

These differentiators are real but not flashy. If we pivot here, we
must invest the demo-video time to *show* the aggregation pipeline on
screen (per `demo-script.md` 2:20–2:40) so the differentiation is
visible to a judge watching 60 of these in a row.

## What we would do next if we pivoted to this project

1. Day 1: wire Vertex AI + MCP + Voyage end-to-end against the stubs
   above; ship a real `/decode` against the seeded data.
2. Day 2: expand the seed dataset to 4 conditions × ~10 docs each
   (thyroid_nodule, lung_nodule, breast_mass, basic CBC abnormality);
   add the banned-phrase post-generation gate in `responder.py`.
3. Day 3: minimal frontend; record demo; freeze.

Anything beyond this — proper auth, BAA-track infra, a second
language, multi-user vault sharing — is out of scope for the
hackathon and should remain so.
