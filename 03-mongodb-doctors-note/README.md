# Doctor's Note Decoder

> You just got home from your appointment. The portal pinged: "Your results
> are ready." You open the PDF. It says *"TIRADS 3 nodule, 2.1 cm, mixed
> echogenicity, no microcalcifications, recommend follow-up ultrasound in
> 12 months."* You have no idea if you are fine or dying. It is 11pm.
> Your doctor's next available call-back is in three days.
>
> This agent reads the literature for you and explains, in plain language,
> what your report says — and gives you three specific questions to ask
> your doctor. It does **not** diagnose. It explains.

**Hackathon:** [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/)
**Submission track:** MongoDB Atlas
**Status:** Active MongoDB build path. This is the clearest route if we are
committing to the MongoDB track and want the partner integration to be
obviously load-bearing.
**Deadline:** June 11, 2026 (2:00 PM PDT)
**License:** Apache-2.0 (added at the workspace root before submission)

---

## The problem

Every adult in America has had this moment. You open the patient portal,
your lab or imaging report is there, and it is written for another
clinician — not for you. The standard 2026 coping strategy is to Google
the terms (which surfaces the worst-case cancer stories on page one),
then dump the report into a general chatbot (which either over-reassures
or hallucinates a diagnosis), then panic until your next appointment.

There is a real information gap between the report and the patient that
the existing tools do not close:

- **Search engines** show worst-case content because that is what gets
  clicks. They do not surface the *base rate* of your specific finding.
- **General chatbots** will happily diagnose you, which is exactly what
  they should not do, and they cite nothing.
- **Patient-facing summaries from the EHR** are pre-generated and generic;
  they do not address the specific phrasing on *your* report.

What patients actually need is (a) a plain-language translation, (b) the
statistical context for their specific finding, and (c) better questions
to ask their doctor. None of that requires a diagnosis.

For the hackathon demo, we deliberately scope v1 to **radiology and imaging
reports first**. That keeps the retrieval domain narrow, makes the Atlas
collections easier to curate, and keeps the safety framing much tighter than a
"general medical copilot."

## The user

**Priya, 41**, just got her thyroid ultrasound report through MyChart.
The radiologist wrote it for an endocrinologist; Priya is a product
manager. Her appointment is in nine days. She does not want to wait nine
days to know whether to be worried. She also does not want to be told a
diagnosis by an AI. She wants to walk into the appointment informed.

## What the agent does

1. **Accepts a medical report** — PDF, image, or pasted text. Gemini 3
   multimodal extracts the medical content faithfully (no rewriting, no
   interpretation at this stage).
2. **Identifies the key medical entities** with structure
   (e.g. `condition=thyroid nodule`, `classification=TIRADS 3`,
   `size_cm=2.1`, `features=[mixed echogenicity, no microcalcifications]`,
   `recommendation=follow-up US in 12mo`).
3. **Runs hybrid retrieval** against a MongoDB Atlas knowledge base:
   - Atlas Vector Search (`$vectorSearch`) over PubMed abstracts and clinical
     guideline excerpts relevant to the extracted finding.
   - Atlas search over de-identified patient-experience snippets so the output
     can explain what follow-up typically feels like without pretending to be a
     diagnosis engine.
   - Structured filters for condition type, severity tier, source type, and
     recency, applied in the same aggregation pipeline.
   - Query and document embeddings generated with **Google Cloud Vertex AI
     text embeddings**, which keeps the project compliant with the hackathon's
     Google-only AI rule.
4. **Produces a structured explanation** (Pydantic-validated JSON):
   - Plain-language translation of what the report says
   - Statistical context for this specific finding (e.g. "TIRADS 3
     nodules carry a roughly 5% malignancy risk in published series")
   - Three specific follow-up questions to ask the doctor
   - Whether a follow-up appointment is likely, and on what timeline
   - A non-negotiable disclaimer block (see `LEGAL-DISCLAIMER.md`)
5. **Optionally saves** the explanation to the patient's private MongoDB
   collection so future reports can be cross-referenced and compared over time.

The agent never says "you have X" or "you do not have X". It explains
the words on the page and the literature around them. The framing is
hard-baked into the system prompt and enforced by the response schema.

## Why this wins the MongoDB track

MongoDB Atlas Vector Search is genuinely load-bearing here, not decorative:

- **Hybrid retrieval in a single aggregation pipeline.** Atlas lets us combine
  `$vectorSearch` with `$match` structured filters and lightweight reranking
  inside one query. That is the right primitive for "find literature and
  guidelines about a mildly suspicious thyroid nodule, favor recent sources,
  and exclude irrelevant conditions."
- **One database, many shapes.** Literature, guideline excerpts,
  patient-experience snippets, and a user's saved history all live in Atlas
  with different schemas but a unified retrieval surface. That flexibility is
  the actual product advantage.
- **Official MongoDB MCP server is visible in the demo.** Judges will see the
  agent using the supported MongoDB tool surface instead of a hidden direct DB
  client.
- **Faster path to a polished submission.** Compared with the multi-partner
  Fivetran build, this path has fewer approval blockers, a narrower surface
  area, and a cleaner 3-minute story.
- **Emotionally strong demo.** The before/after is immediate: incomprehensible
  report in, plain-language explanation with cited context out.

## Hackathon resource alignment

This path lines up cleanly with the official resource phases:

- **Core frameworks & environment:** Google Cloud trial/credits, Vertex AI,
  Agent Builder or Agent Runtime, Atlas free tier.
- **Action mechanisms & data connectivity:** official MongoDB MCP server as the
  tool surface; Atlas as the source of truth instead of a decorative side store.
- **Reasoning, state, & logic hosting:** Python agent on Cloud Run or Agent
  Runtime, with patient-history state persisted in Atlas.
- **Deployment & safety:** Secret Manager for secrets, Gemini safety settings,
  Cloud Run deployment, and a public hosted URL for judging.

See [`build-plan.md`](./build-plan.md) for the revised execution path.

## Stack

| Layer | Tech |
|---|---|
| Agent runtime | Google Cloud **Agent Builder** or **Agent Runtime** + **Gemini 3** via Vertex AI |
| Multimodal extraction | Gemini 3 vision (PDF / image / text) |
| Vector database | **MongoDB Atlas** with Atlas Vector Search |
| Embeddings | **Vertex AI text embeddings** |
| MCP server | [Official MongoDB MCP server](https://www.mongodb.com/docs/mcp-server/tools/) |
| Agent service | Python 3.11, FastAPI on Cloud Run |
| Secrets & safety | Secret Manager + Gemini safety settings |
| Frontend | Minimal upload UI for the demo, polished only where it helps judging |
| Repo | Public GitHub, Apache-2.0 |

See [`architecture.md`](./architecture.md) for the full system diagram
and data flow.

## Repository layout

```
03-mongodb-doctors-note/
├── README.md                    (this file)
├── architecture.md              (system diagram, data flow)
├── build-plan.md                (resource-aligned build plan)
├── demo-script.md               (3-minute video script)
├── LEGAL-DISCLAIMER.md          (the exact disclaimer text shipped in the product)
├── SCAFFOLD-NOTES.md            (what is done, what is stubbed, risks)
└── agent/
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── main.py                  (FastAPI: /decode endpoint)
    ├── extractor.py             (Gemini 3 multimodal -> medical entities)
    ├── retriever.py             (Mongo MCP $vectorSearch hybrid retrieval)
    ├── responder.py             (entities + retrieval -> Pydantic response)
    ├── prompts.py               (system prompt with hard-baked disclaimer)
    └── seed_data.py             (seed Atlas with sample literature/guidelines/forum data)
```

## Quick start

```bash
cd agent
cp .env.example .env
# Fill in MONGODB_URI, GOOGLE_CLOUD_PROJECT, VERTEX_EMBEDDING_MODEL, etc.

python -m venv .venv && source .venv/bin/activate
pip install -e .

python seed_data.py            # populate the Atlas knowledge base
uvicorn main:app --reload --port 8080
```

Then `POST /decode` with a medical report (PDF / image / pasted text) and
get back the structured explanation.

## Status

This scaffold is now the active MongoDB route. See
[`SCAFFOLD-NOTES.md`](./SCAFFOLD-NOTES.md) for what is wired up versus stubbed,
and [`build-plan.md`](./build-plan.md) for the revised sprint from here to a
submission-ready demo.

## License

Apache-2.0 (will be added at the workspace root before submission, per the
hackathon's OSI license requirement).
