"""Hybrid retrieval over the MongoDB Atlas knowledge base via the
official MongoDB MCP server.

Why this lives in its own module:
    Retrieval is the part of the system most likely to evolve quickly
    (we will tune k, filter weights, recency reranking, and which
    collections to hit per query). Keeping the synthesis layer free of
    Mongo / MCP detail means we can iterate on retrieval without
    touching the prompt or the response schema.

    The MCP server is the only thing that talks to Atlas in production.
    The agent process never opens a raw MongoClient against the cluster
    on the request path. This module owns the MCP session and the
    aggregation-pipeline construction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from extractor import ExtractedReport


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RetrievedDoc:
    """One document returned by retrieval, normalized across collections."""

    collection: str
    title: str
    snippet: str
    source: str  # e.g. "pubmed", "acr_tirads_2017", "forum:reddit_thyroid"
    url: str | None
    published_year: int | None
    score: float


@dataclass
class RetrievalBundle:
    """Everything the responder needs from the knowledge base."""

    literature: list[RetrievedDoc]
    guidelines: list[RetrievedDoc]
    forum_posts: list[RetrievedDoc]


# ---------------------------------------------------------------------------
# Pipeline construction (pure: easy to unit-test once tests land)
# ---------------------------------------------------------------------------


def build_pipeline(
    *,
    query_text: str,
    condition: str | None,
    severity_tier: str | None,
    min_year: int = 2018,
    k: int = 5,
    num_candidates: int = 200,
    vector_index: str = "vector_index",
) -> list[dict[str, Any]]:
    """Build a single `$vectorSearch` aggregation pipeline.

    Design notes:
      * We push structured filters into `$vectorSearch.filter` so Atlas
        prunes candidates BEFORE the ANN search; without this, semantic
        recall happily pulls a 2003 case report from a different patient
        population.
      * `numCandidates` is generous (200) because the filtered surface is
        small per (condition, severity_tier) cell; raising it costs
        little and improves recall.
      * We pass `query_text` straight through; Atlas / Voyage do the
        embedding server-side when the index is configured with an
        embedding model. If we ever switch to client-side embeddings we
        replace `queryText` with `queryVector` here.
    """

    vector_filter: dict[str, Any] = {"language": {"$eq": "en"}}
    if condition:
        vector_filter["condition"] = {"$eq": condition}
    if severity_tier:
        vector_filter["severity_tier"] = {"$eq": severity_tier}
    vector_filter["published_year"] = {"$gte": min_year}

    return [
        {
            "$vectorSearch": {
                "index": vector_index,
                "path": "embedding",
                "queryText": query_text,
                "numCandidates": num_candidates,
                "limit": k,
                "filter": vector_filter,
            }
        },
        # Project a normalized shape so downstream code is collection-agnostic.
        {
            "$project": {
                "_id": 0,
                "title": 1,
                "snippet": {"$ifNull": ["$abstract", "$text"]},
                "source": 1,
                "url": 1,
                "published_year": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]


# ---------------------------------------------------------------------------
# MCP-driven retrieval (stubbed)
# ---------------------------------------------------------------------------


async def retrieve(extracted: ExtractedReport, *, k: int = 5) -> RetrievalBundle:
    """Run hybrid retrieval across literature, guidelines, and forum posts.

    Implementation outline (post-stub):
      1. Compose a `query_text` from the extracted entities. We use the
         report's modality + body_site + the top-N entity names/values
         rather than the raw report text, so the embedding reflects the
         clinical question, not boilerplate header text.
      2. Build three pipelines (literature, guidelines, forum_posts) with
         build_pipeline().
      3. Send each to the MCP server's `aggregate` tool. The Python MCP
         client (`mcp` package) gives us a typed call:
             session.call_tool(
                 "aggregate",
                 {"database": MONGODB_DB,
                  "collection": "literature",
                  "pipeline": pipeline}
             )
      4. Normalize results into RetrievedDoc and bundle.

    The stub here returns a small fixed bundle so the rest of the system
    is independently runnable.
    """

    db = os.getenv("MONGODB_DB", "doctors_note")
    _ = db  # referenced for completeness; real impl uses it in MCP call args

    query_text = _compose_query_text(extracted)
    pipeline_lit = build_pipeline(
        query_text=query_text,
        condition=extracted.primary_condition,
        severity_tier=extracted.severity_tier_guess,
        k=k,
    )
    pipeline_guide = build_pipeline(
        query_text=query_text,
        condition=extracted.primary_condition,
        severity_tier=None,  # guidelines apply across severity tiers
        k=3,
    )
    pipeline_forum = build_pipeline(
        query_text=query_text,
        condition=extracted.primary_condition,
        severity_tier=extracted.severity_tier_guess,
        k=k,
    )
    # TODO replace with real MCP calls:
    #   from mcp import ClientSession
    #   ... session.call_tool("aggregate", {...})
    _ = (pipeline_lit, pipeline_guide, pipeline_forum)

    return RetrievalBundle(
        literature=[
            RetrievedDoc(
                collection="literature",
                title="Risk of malignancy in TIRADS 3 thyroid nodules: a meta-analysis",
                snippet=(
                    "Across 12 studies (n=3,412), TIRADS 3 nodules carried a pooled "
                    "malignancy risk of ~5%; risk did not differ significantly by "
                    "nodule size below 2.5 cm."
                ),
                source="pubmed",
                url="https://pubmed.ncbi.nlm.nih.gov/SAMPLE-0001",
                published_year=2023,
                score=0.82,
            ),
        ],
        guidelines=[
            RetrievedDoc(
                collection="guidelines",
                title="ACR TI-RADS, 2017",
                snippet=(
                    "TIRADS 3 nodules >=2.5 cm: follow-up ultrasound in 1, 3, and 5 "
                    "years. <2.5 cm: follow-up at 12 months."
                ),
                source="acr_tirads_2017",
                url="https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/TI-RADS",
                published_year=2017,
                score=0.78,
            ),
        ],
        forum_posts=[
            RetrievedDoc(
                collection="forum_posts",
                title="Got a TIRADS 3 result, doctor said wait 12 months — anyone else?",
                snippet=(
                    "Several commenters describe being given a 12-month US follow-up "
                    "and asking for a baseline TSH; most reported no change at follow-up."
                ),
                source="forum:reddit_thyroid",
                url=None,
                published_year=2024,
                score=0.71,
            ),
        ],
    )


def _compose_query_text(extracted: ExtractedReport) -> str:
    """Project an ExtractedReport down to a clinical-question string.

    We deliberately drop the report's header / boilerplate to keep the
    embedding focused. Order matters: modality + body_site first, then
    the scored finding, then descriptors.
    """

    parts: list[str] = []
    if extracted.modality:
        parts.append(extracted.modality)
    if extracted.body_site:
        parts.append(extracted.body_site)
    for entity in extracted.entities:
        if entity.value is not None:
            unit = f" {entity.units}" if entity.units else ""
            parts.append(f"{entity.name} {entity.value}{unit}")
        for q in entity.qualifiers:
            parts.append(q)
    return "; ".join(parts)
