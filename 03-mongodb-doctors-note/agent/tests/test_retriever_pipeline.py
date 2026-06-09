"""Tests for the pure aggregation-pipeline builder.

These need no MongoDB, no MCP, and no network: build_pipeline() is a pure
function, which is exactly why it lives apart from the MCP dispatch.
"""

from __future__ import annotations

from retriever import build_pipeline


def test_pipeline_shape_is_vectorsearch_then_project():
    pipeline = build_pipeline(
        query_vector=[0.0] * 8,
        condition="thyroid_nodule",
        severity_tier="low",
    )
    assert [next(iter(stage)) for stage in pipeline] == ["$vectorSearch", "$project"]


def test_filters_are_pushed_into_vectorsearch():
    pipeline = build_pipeline(
        query_vector=[0.0] * 8,
        condition="lung_nodule",
        severity_tier="moderate",
        min_year=2019,
    )
    vfilter = pipeline[0]["$vectorSearch"]["filter"]
    assert vfilter["condition"] == {"$eq": "lung_nodule"}
    assert vfilter["severity_tier"] == {"$eq": "moderate"}
    assert vfilter["published_year"] == {"$gte": 2019}
    assert vfilter["language"] == {"$eq": "en"}


def test_optional_filters_are_omitted_when_absent():
    pipeline = build_pipeline(
        query_vector=[0.0] * 8,
        condition=None,
        severity_tier=None,
    )
    vfilter = pipeline[0]["$vectorSearch"]["filter"]
    assert "condition" not in vfilter
    assert "severity_tier" not in vfilter
    # language + published_year are always present.
    assert "language" in vfilter
    assert "published_year" in vfilter


def test_k_controls_limit_and_candidates_default():
    pipeline = build_pipeline(query_vector=[0.0] * 8, condition=None, severity_tier=None, k=3)
    vs = pipeline[0]["$vectorSearch"]
    assert vs["limit"] == 3
    assert vs["numCandidates"] == 200
    assert vs["path"] == "embedding"
