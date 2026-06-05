"""Seed the MongoDB Atlas knowledge base with sample documents.

Why this is a separate script (not part of the request path):
    Seeding touches schema (collections, vector indexes), which we want
    to be an explicit, opt-in operation — not something that runs on
    every cold start. It is also the one place we use `pymongo` directly:
    the MCP server is the right surface for retrieval, but the MCP
    server's `create-index` tool exists to create Vector Search indexes
    too. We use it here to keep the production data path going through
    MCP end-to-end.

What lands where:
    - literature      sample PubMed-style abstracts (clearly labeled samples)
    - guidelines      sample guideline excerpts (ACR TI-RADS, ATA)
    - forum_posts     FABRICATED forum-style entries, labeled is_sample=True
                      and source="sample:fabricated". Do NOT seed real forum
                      content without consent / TOS compliance review (see
                      ../LEGAL-DISCLAIMER.md, "Scope of data we will and will
                      not seed").

This is a backup-scaffold-tier seed: enough to wire up vector search
end-to-end with one realistic-looking condition (thyroid_nodule). Expand
breadth before any public demo.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# We import pymongo lazily and only for the index bootstrap path so that
# the rest of the application has no runtime dependency on it. Keep it
# this way: if the seed script grows complicated, factor it out, not in.
try:
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(
        "pymongo is not installed. Run `pip install -e .` from agent/.\n"
    )
    raise SystemExit(1) from exc

from vertex_ai import embed_text, get_embedding_dimensions


# ---------------------------------------------------------------------------
# Sample documents. Deliberately minimal; expand for real demo.
# ---------------------------------------------------------------------------

SAMPLE_LITERATURE: list[dict[str, Any]] = [
    {
        "_id": "sample-pubmed-tirads3-meta-2023",
        "title": "Risk of malignancy in TIRADS 3 thyroid nodules: a meta-analysis",
        "abstract": (
            "Across 12 studies (n=3,412), TIRADS 3 thyroid nodules carried "
            "a pooled malignancy risk of approximately 5%. Risk did not "
            "differ significantly by nodule size below 2.5 cm. Watchful "
            "surveillance with interval ultrasound was the most common "
            "downstream management."
        ),
        "condition": "thyroid_nodule",
        "severity_tier": "low",
        "source": "pubmed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/SAMPLE-0001",
        "published_year": 2023,
        "language": "en",
        "is_sample": True,
    },
    {
        "_id": "sample-pubmed-tirads3-growth-2022",
        "title": (
            "Growth patterns of TIRADS 3 thyroid nodules over 24-month "
            "surveillance: a prospective cohort"
        ),
        "abstract": (
            "Of 412 TIRADS 3 nodules followed prospectively for 24 months, "
            "fewer than 10% demonstrated growth meeting criteria for "
            "biopsy upgrade. Most clinically meaningful changes occurred "
            "between months 12 and 24."
        ),
        "condition": "thyroid_nodule",
        "severity_tier": "low",
        "source": "pubmed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/SAMPLE-0002",
        "published_year": 2022,
        "language": "en",
        "is_sample": True,
    },
]

SAMPLE_GUIDELINES: list[dict[str, Any]] = [
    {
        "_id": "sample-acr-tirads-2017-excerpt",
        "title": "ACR TI-RADS, 2017 (excerpt)",
        "text": (
            "TIRADS 3 (mildly suspicious): nodules >=2.5 cm should undergo "
            "FNA; nodules <2.5 cm should undergo follow-up ultrasound at "
            "1, 3, and 5 years."
        ),
        "condition": "thyroid_nodule",
        "severity_tier": "low",
        "source": "acr_tirads_2017",
        "url": (
            "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/TI-RADS"
        ),
        "published_year": 2017,
        "language": "en",
        "is_sample": True,
    },
    {
        "_id": "sample-ata-2015-excerpt",
        "title": "ATA Management Guidelines for Adult Patients with Thyroid Nodules (2015, excerpt)",
        "text": (
            "Baseline TSH measurement is recommended for all patients with a "
            "thyroid nodule. Sonographic features (composition, echogenicity, "
            "shape, margin, echogenic foci) determine FNA thresholds."
        ),
        "condition": "thyroid_nodule",
        "severity_tier": "low",
        "source": "ata_2015",
        "url": "https://www.thyroid.org/professionals/ata-professional-guidelines/",
        "published_year": 2015,
        "language": "en",
        "is_sample": True,
    },
]

SAMPLE_FORUM: list[dict[str, Any]] = [
    {
        "_id": "sample-forum-tirads3-12mo",
        "title": "Got a TIRADS 3 result, doctor said wait 12 months — anyone else?",
        "text": (
            "FABRICATED SAMPLE for hackathon scaffold. Commenters describe "
            "being given a 12-month US follow-up after a TIRADS 3 result, "
            "asking for baseline TSH at the visit, and reporting no change "
            "at the 12-month follow-up."
        ),
        "condition": "thyroid_nodule",
        "severity_tier": "low",
        "source": "sample:fabricated",
        "url": None,
        "published_year": 2024,
        "language": "en",
        "is_sample": True,
    },
]


# ---------------------------------------------------------------------------
# Index spec. One vector index per vector-bearing collection. The path
# `embedding` is populated client-side with Vertex embeddings during the
# seed step so Atlas Vector Search is usable immediately.
# ---------------------------------------------------------------------------


def _vector_index_definition(num_dims: int) -> dict[str, Any]:
    return {
        "name": "vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": num_dims,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "condition"},
                {"type": "filter", "path": "severity_tier"},
                {"type": "filter", "path": "source"},
                {"type": "filter", "path": "published_year"},
                {"type": "filter", "path": "language"},
            ]
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    uri = os.environ["MONGODB_URI"]
    db_name = os.getenv("MONGODB_DB", "doctors_note")
    num_dims = get_embedding_dimensions()

    client = MongoClient(uri)
    db = client[db_name]

    plan = [
        (os.getenv("MONGODB_COLLECTION_LITERATURE", "literature"), SAMPLE_LITERATURE),
        (os.getenv("MONGODB_COLLECTION_GUIDELINES", "guidelines"), SAMPLE_GUIDELINES),
        (os.getenv("MONGODB_COLLECTION_FORUM", "forum_posts"), SAMPLE_FORUM),
    ]

    for coll_name, docs in plan:
        coll = db[coll_name]

        for doc in docs:
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": _with_embedding(doc)},
                upsert=True,
            )

        try:
            coll.create_search_index(model=_vector_index_definition(num_dims))
        except OperationFailure as exc:
            # IndexAlreadyExists or driver-version variant: ignore.
            sys.stderr.write(
                f"[seed_data] index on {coll_name} not (re)created: {exc}\n"
            )

        print(f"[seed_data] {coll_name}: {len(docs)} sample docs upserted")

    print(
        "[seed_data] DONE. Atlas documents now include client-side Vertex "
        "embeddings, so vector search can run immediately once the Atlas "
        "index finishes building."
    )


def _with_embedding(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a seed document with an `embedding` field attached."""

    out = dict(doc)
    out["embedding"] = embed_text(
        _embedding_source_text(doc),
        task_type="RETRIEVAL_DOCUMENT",
        title=str(doc.get("title") or ""),
    )
    return out


def _embedding_source_text(doc: dict[str, Any]) -> str:
    """Compose the text chunk that should represent a seed document."""

    parts = [
        str(doc.get("title") or "").strip(),
        str(doc.get("abstract") or "").strip(),
        str(doc.get("text") or "").strip(),
        str(doc.get("condition") or "").strip(),
        str(doc.get("severity_tier") or "").strip(),
    ]
    return "\n\n".join(part for part in parts if part)


if __name__ == "__main__":
    main()
