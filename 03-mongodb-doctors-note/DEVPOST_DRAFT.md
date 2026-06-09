# Devpost draft — Doctor's Note Decoder

> Submission track: **MongoDB Atlas**
> Hackathon: Google Cloud Rapid Agent Hackathon
> One-liner: *An agent that explains your medical report in plain language —
> grounded in real literature retrieved from MongoDB Atlas — and never diagnoses.*

Paste these sections into the Devpost fields. Keep the lower-third disclaimer
band visible for the entire demo video (see `demo-script.md`).

---

## Inspiration

Everyone has had this moment: the patient portal pings, "your results are
ready," you open the PDF, and it's written for another clinician — not for
you. *"TIRADS 3 nodule, 2.1 cm, mixed echogenicity, recommend follow-up
ultrasound in 12 months."* It's 11pm and your doctor's next callback is in
three days. So you Google the terms (page one is worst-case cancer stories)
and then paste it into a general chatbot, which either over-reassures you or
confidently hallucinates a diagnosis it has no business giving.

There's a real gap between the report and the patient that today's tools
don't close. We didn't want to build another chatbot that diagnoses. We
wanted to build the thing that's actually safe and actually useful: a tool
that **explains the words on the page and the published evidence around
them**, and sends you into your appointment informed.

## What it does

You give it a medical report — PDF, image, or pasted text. The agent:

1. **Extracts** the medical content faithfully with Gemini multimodal (it
   structures what the report *says*; it does not interpret).
2. **Retrieves** relevant evidence from a MongoDB Atlas knowledge base using
   Atlas Vector Search — published literature, clinical guideline excerpts,
   and de-identified patient-experience snippets — filtered by condition,
   severity tier, recency, and language in a single aggregation.
3. **Explains**, returning a structured response: a plain-language
   translation, the *statistical context* for your specific finding
   (e.g. "TIRADS 3 nodules carry a roughly 5% malignancy risk in published
   series"), three specific questions to ask your clinician, and the likely
   follow-up timeline.

It **never** says "you have X" or "you don't have X." That rule is baked into
the system prompt, enforced by the response schema, and double-checked by a
diagnostic-language gate on the generated text. If the model ever drifts into
diagnostic phrasing, we discard that response and return a safe one.

## How we built it

**Stack:** Google Cloud Vertex AI (Gemini for extraction + synthesis,
`gemini-embedding-001` for embeddings) · MongoDB Atlas Vector Search via the
**official MongoDB MCP server** · Python 3.11 + FastAPI on Cloud Run.

The agent is four clean components behind a thin FastAPI service:

- **`extractor.py`** — Gemini multimodal turns a PDF/image/text report into a
  structured `ExtractedReport` (modality, body site, entities, a canonical
  condition tag, and a coarse severity tier derived from the report's own
  scoring system — TIRADS/BI-RADS/Fleischner — never our judgment).
- **`retriever.py`** — the load-bearing MongoDB piece. We embed the clinical
  question (not the boilerplate report header) with Vertex, then run a single
  `$vectorSearch` aggregation per collection with structured pre-filters
  pushed *into* the vector search, so Atlas prunes candidates by condition,
  severity, year, and language **before** the ANN step. All Atlas access goes
  through the official MongoDB MCP server — judges see the supported tool
  surface, not a hidden DB client.
- **`responder.py`** — Gemini structured output produces a Pydantic-validated
  `DecodedReport`. Two model validators enforce the product's invariants (a
  non-empty legal disclaimer; the follow-up must reference the clinician), and
  a high-precision regex gate catches any diagnostic language that slips past
  the prompt and routes to a safe fallback.
- **`seed_data.py`** — seeds the Atlas collections with clearly-labeled sample
  literature, guidelines, and fabricated patient-experience snippets across
  four conditions, and creates the Atlas Vector Search index with dimensions
  centralized so they can never drift from the embedding model.

The single-page UI is served by the same FastAPI app (one Cloud Run service,
no separate frontend build, no CORS), and surfaces the Atlas retrieval results
as a dedicated panel — so you can literally watch MongoDB doing the work.

## Why MongoDB Atlas is genuinely load-bearing

Atlas isn't a decorative side store here — it's the grounding engine:

- **Hybrid retrieval in one aggregation pipeline.** `$vectorSearch` combined
  with structured pre-filters and `vectorSearchScore` projection in a single
  query is exactly the right primitive for "find literature and guidelines
  about a mildly suspicious thyroid nodule, favor recent sources, exclude
  other conditions."
- **One database, many shapes.** Literature, guideline excerpts,
  patient-experience snippets, and a user's saved history live in Atlas with
  different schemas behind one unified retrieval surface.
- **Official MongoDB MCP server** is visible in the demo as the agent's tool
  surface — the supported, agent-native way to talk to Atlas.

## Challenges we ran into

- **Safety as an engineering problem, not a disclaimer.** Making "explains,
  never diagnoses" a *guarantee* meant three layers — system prompt, schema
  validators, and a prose-level diagnostic-language gate that's precise enough
  to catch "you have cancer" while never tripping on "your report describes…"
  or "you may want to ask your clinician whether…".
- **Demo resilience.** A live agent demo dies if any dependency hiccups, so
  retrieval and synthesis both degrade gracefully — the service keeps serving
  and returns a safe, sourced response even if the MCP subprocess or Vertex
  is briefly unavailable.
- **Embedding/index alignment.** Vector dimensions are centralized in one
  config and asserted at seed time so the Atlas index and the embedding model
  can never silently drift out of sync.

## What's next

- Broaden the corpus beyond the four demo conditions with a proper ingestion
  pipeline for guideline and literature sources.
- Patient "vault" history in Atlas to answer "has this changed since last
  time?" across reports.
- A real auth layer in front of saved history (the demo uses a static token).

## Built with

`google-cloud` · `vertex-ai` · `gemini` · `mongodb-atlas` ·
`atlas-vector-search` · `mongodb-mcp-server` · `python` · `fastapi` ·
`pydantic` · `cloud-run`
