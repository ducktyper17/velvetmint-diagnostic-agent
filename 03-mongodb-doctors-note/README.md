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
**Status:** Backup submission. The primary submission is the Fivetran DTC
Diagnostic in `../01-fivetran-dtc-diagnostic/`. This project exists in case
we hit a Day-4 pivot gate (see `../DECISION.md`).
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
   - Vector search (Voyage AI embeddings, `$vectorSearch` aggregation)
     over PubMed abstracts and clinical guidelines for the relevant
     condition.
   - Vector search over de-identified patient-forum excerpts to capture
     what the experience and decision-making typically look like.
   - Structured filters for condition type, severity tier, and source
     recency, applied in the same aggregation pipeline.
4. **Produces a structured explanation** (Pydantic-validated JSON):
   - Plain-language translation of what the report says
   - Statistical context for this specific finding (e.g. "TIRADS 3
     nodules carry a roughly 5% malignancy risk in published series")
   - Three specific follow-up questions to ask the doctor
   - Whether a follow-up appointment is likely, and on what timeline
   - A non-negotiable disclaimer block (see `LEGAL-DISCLAIMER.md`)
5. **Optionally saves** the explanation to the patient's private
   MongoDB collection so future reports can be cross-referenced.

The agent never says "you have X" or "you do not have X". It explains
the words on the page and the literature around them. The framing is
hard-baked into the system prompt and enforced by the response schema.

## Why this fits the MongoDB track

MongoDB Atlas Vector Search is genuinely load-bearing here, not
decorative:

- **Hybrid retrieval in a single aggregation pipeline.** Atlas lets us
  combine `$vectorSearch` with `$match` structured filters and
  `$rankFusion`-style scoring inside one Mongo query. That is the right
  primitive for "semantically similar literature about TIRADS 3 nodules,
  published after 2022, in English."
- **Auto-embedding on insert via the official MongoDB MCP server.** When
  `VOYAGE_API_KEY` is set, the MCP server's `insert-many` tool can embed
  text fields automatically as documents go in. This removes a whole
  embedding pipeline from our code path.
- **One database, many shapes.** Literature, guidelines, forum excerpts,
  and the patient's saved history all live in Atlas with different
  schemas but unified search. That is the document model's strength and
  it is hard to express as cleanly in a row-store.

## Stack

| Layer | Tech |
|---|---|
| Agent runtime | Google Cloud **Agent Builder** + **Gemini 3** via Vertex AI |
| Multimodal extraction | Gemini 3 vision (PDF / image / text) |
| Vector database | **MongoDB Atlas** with Atlas Vector Search |
| Embeddings | **Voyage AI** (`voyage-3-large`, or `voyage-medical` if available) |
| MCP server | [Official MongoDB MCP server](https://www.mongodb.com/docs/mcp-server/tools/) |
| Agent service | Python 3.11, FastAPI on Cloud Run |
| Frontend | Minimal HTML form for the demo (full UI is post-pivot work) |
| Repo | Public GitHub, Apache-2.0 |

See [`architecture.md`](./architecture.md) for the full system diagram
and data flow.

## Repository layout

```
03-mongodb-doctors-note/
├── README.md                    (this file)
├── architecture.md              (system diagram, data flow)
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
# Fill in MONGODB_URI, VOYAGE_API_KEY, GOOGLE_CLOUD_PROJECT, etc.

python -m venv .venv && source .venv/bin/activate
pip install -e .

python seed_data.py            # populate the Atlas knowledge base
uvicorn main:app --reload --port 8080
```

Then `POST /decode` with a medical report (PDF / image / pasted text) and
get back the structured explanation.

## Status

This is a backup-tier scaffold (roughly 60% of the depth we would put
into the primary submission). See [`SCAFFOLD-NOTES.md`](./SCAFFOLD-NOTES.md)
for what is wired up versus stubbed, the work-hours estimate to a
demo-able state, and the top risks (the legal/medical framing risk is
listed first and is the one that decides whether this project ships at
all).

## License

Apache-2.0 (will be added at the workspace root before submission, per the
hackathon's OSI license requirement).
