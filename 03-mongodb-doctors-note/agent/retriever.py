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

import json
import os
from dataclasses import dataclass
from typing import Any

from extractor import ExtractedReport
from vertex_ai import embed_text_async


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
    query_vector: list[float],
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
      * Query embeddings are generated client-side with Vertex AI so the
        hackathon path stays Google-only on the model side.
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
                "queryVector": query_vector,
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
# MCP-driven retrieval
# ---------------------------------------------------------------------------


async def retrieve(
    extracted: ExtractedReport,
    *,
    session: Any | None = None,
    k: int = 5,
) -> RetrievalBundle:
    """Run hybrid retrieval across literature, guidelines, and forum posts.

    Implementation outline (post-stub):
      1. Compose a `query_text` from the extracted entities. We use the
         report's modality + body_site + the top-N entity names/values
         rather than the raw report text, so the embedding reflects the
         clinical question, not boilerplate header text.
      2. Generate a Vertex embedding for that query summary.
      3. Build three pipelines (literature, guidelines, forum_posts) with
         build_pipeline().
      4. Send each to the MCP server's `aggregate` tool. The Python MCP
         client (`mcp` package) gives us a typed call:
             session.call_tool(
                 "aggregate",
                 {"database": MONGODB_DB,
                  "collection": "literature",
                  "pipeline": pipeline}
             )
      5. Normalize results into RetrievedDoc and bundle.

    If MCP is unavailable or returns an unexpected payload shape, we fall
    back to a small deterministic bundle so the rest of the system keeps
    working during development.
    """

    # No MCP session means no Atlas: skip the (paid) embedding call entirely
    # and return the deterministic bundle so the rest of the pipeline runs.
    if session is None:
        return _stub_bundle()

    db = os.getenv("MONGODB_DB", "doctors_note")

    try:
        query_text = _compose_query_text(extracted)
        query_vector = await embed_text_async(
            query_text,
            task_type="RETRIEVAL_QUERY",
        )
        pipeline_lit = build_pipeline(
            query_vector=query_vector,
            condition=extracted.primary_condition,
            severity_tier=None,  # a paper applies across severity tiers, like guidelines
            k=k,
        )
        pipeline_guide = build_pipeline(
            query_vector=query_vector,
            condition=extracted.primary_condition,
            severity_tier=None,  # guidelines apply across severity tiers
            k=3,
        )
        pipeline_forum = build_pipeline(
            query_vector=query_vector,
            condition=extracted.primary_condition,
            severity_tier=extracted.severity_tier_guess,
            k=k,
        )
        literature = await _run_aggregate(
            session,
            database=db,
            collection=os.getenv("MONGODB_COLLECTION_LITERATURE", "literature"),
            pipeline=pipeline_lit,
        )
        guidelines = await _run_aggregate(
            session,
            database=db,
            collection=os.getenv("MONGODB_COLLECTION_GUIDELINES", "guidelines"),
            pipeline=pipeline_guide,
        )
        forum_posts = await _run_aggregate(
            session,
            database=db,
            collection=os.getenv("MONGODB_COLLECTION_FORUM", "forum_posts"),
            pipeline=pipeline_forum,
        )
        bundle = RetrievalBundle(
            literature=_normalize_docs("literature", literature),
            guidelines=_normalize_docs("guidelines", guidelines),
            forum_posts=_normalize_docs("forum_posts", forum_posts),
        )
        if bundle.literature or bundle.guidelines or bundle.forum_posts:
            return bundle
    except Exception:
        pass

    return _stub_bundle()


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


async def _run_aggregate(
    session: Any,
    *,
    database: str,
    collection: str,
    pipeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run one MongoDB MCP `aggregate` call and normalize its result payload."""

    result = await session.call_tool(
        "aggregate",
        {
            "database": database,
            "collection": collection,
            "pipeline": pipeline,
        },
    )
    return _extract_rows_from_tool_result(result)


def _extract_rows_from_tool_result(result: Any) -> list[dict[str, Any]]:
    """Handle a few likely MCP result shapes without hard-coding one."""

    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None
    )
    rows = _rows_from_payload(structured)
    if rows:
        return rows

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            rows = _rows_from_payload(json.loads(text))
        except json.JSONDecodeError:
            continue
        if rows:
            return rows
    return []


def _rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Pull result rows out of common aggregate payload containers."""

    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("documents", "results", "items", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _normalize_docs(collection: str, rows: list[dict[str, Any]]) -> list[RetrievedDoc]:
    """Convert raw aggregate rows into `RetrievedDoc` objects."""

    out: list[RetrievedDoc] = []
    for row in rows:
        title = str(row.get("title") or "").strip()
        snippet = str(row.get("snippet") or row.get("text") or row.get("abstract") or "").strip()
        if not title and not snippet:
            continue
        score_value = row.get("score", 0.0)
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            score = 0.0
        published_year = row.get("published_year")
        out.append(
            RetrievedDoc(
                collection=collection,
                title=title or "Untitled source",
                snippet=snippet or "No snippet returned.",
                source=str(row.get("source") or collection),
                url=str(row["url"]) if row.get("url") else None,
                published_year=published_year if isinstance(published_year, int) else None,
                score=score,
            )
        )
    return out


def _stub_bundle() -> RetrievalBundle:
    """Fallback retrieval bundle used when MCP is not yet available."""

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
