"""Integration test for the real MCP retrieval path.

The other tests cover pure logic and the fallback path. This one drives
retriever.retrieve() the way a live request does — through the MCP
`aggregate` call — but with a fake MCP session that returns
Atlas-shaped rows and a stubbed Vertex embedding. It proves that real
retrieved documents flow through pipeline construction, the aggregate
dispatch, and normalization into the bundle the responder consumes.
"""

from __future__ import annotations

import asyncio

import pytest

import retriever
from extractor import ExtractedReport, MedicalEntity


class _FakeResult:
    """Mimics an MCP CallToolResult carrying structured rows."""

    def __init__(self, rows):
        self.structured_content = rows
        self.content = []


class _FakeSession:
    """Stand-in MCP session that records calls and returns canned rows."""

    def __init__(self, rows_by_collection):
        self._rows = rows_by_collection
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return _FakeResult(self._rows.get(args["collection"], []))


@pytest.fixture(autouse=True)
def _stub_embedding(monkeypatch):
    """Avoid a real Vertex call; retrieval only needs *a* query vector."""

    async def fake_embed(text, *, task_type, title=None):
        return [0.0] * 8

    monkeypatch.setattr(retriever, "embed_text_async", fake_embed)


@pytest.fixture
def extracted() -> ExtractedReport:
    return ExtractedReport(
        is_medical_report=True,
        raw_text="Thyroid ultrasound: 2.1 cm nodule, TIRADS 3.",
        modality="thyroid ultrasound",
        body_site="right thyroid lobe",
        entities=[MedicalEntity(name="nodule_size", value=2.1, units="cm")],
        primary_condition="thyroid_nodule",
        severity_tier_guess="low",
    )


def test_real_path_normalizes_atlas_rows(extracted):
    rows = {
        "literature": [
            {
                "title": "TIRADS 3 malignancy risk meta-analysis",
                "snippet": "Pooled malignancy risk ~5%.",
                "source": "pubmed",
                "url": "https://pubmed.ncbi.nlm.nih.gov/SAMPLE-0001",
                "published_year": 2023,
                "score": 0.82,
            }
        ],
        "guidelines": [
            {
                "title": "ACR TI-RADS 2017",
                "snippet": "Follow-up US in 12 months.",
                "source": "acr_tirads_2017",
                "url": None,
                "published_year": 2017,
                "score": 0.77,
            }
        ],
        "forum_posts": [
            {
                "title": "TIRADS 3, told to wait 12 months",
                "snippet": "No change at follow-up.",
                "source": "forum:reddit_thyroid",
                "published_year": 2024,
                "score": 0.6,
            }
        ],
    }
    session = _FakeSession(rows)

    bundle = asyncio.run(retriever.retrieve(extracted, session=session))

    # Real rows came back (not the deterministic stub bundle).
    assert len(bundle.literature) == 1
    assert bundle.literature[0].source == "pubmed"
    assert bundle.literature[0].score == pytest.approx(0.82)
    assert bundle.guidelines[0].url is None
    assert bundle.forum_posts[0].title.startswith("TIRADS 3")

    # The agent talked to Atlas only through the MCP `aggregate` tool.
    assert {name for name, _ in session.calls} == {"aggregate"}
    # Structured pre-filters were pushed into $vectorSearch for the condition.
    lit_pipeline = next(
        args["pipeline"] for name, args in session.calls if args["collection"] == "literature"
    )
    assert lit_pipeline[0]["$vectorSearch"]["filter"]["condition"] == {"$eq": "thyroid_nodule"}


def test_empty_atlas_result_falls_back_to_stub(extracted):
    session = _FakeSession({})  # every collection returns no rows
    bundle = asyncio.run(retriever.retrieve(extracted, session=session))
    # Falls back so the rest of the pipeline still has something to explain.
    assert bundle.literature and bundle.literature[0].source == "pubmed"


def test_rows_parsed_from_text_content_shape(extracted):
    """Some MCP servers return rows as JSON text in `content`, not structured."""

    import json

    class _TextItem:
        def __init__(self, text):
            self.text = text

    class _TextResult:
        def __init__(self, rows):
            self.structured_content = None
            self.content = [_TextItem(json.dumps(rows))]

    class _TextSession:
        def __init__(self, rows):
            self._rows = rows

        async def call_tool(self, name, args):
            return _TextResult(self._rows.get(args["collection"], []))

    rows = {
        "literature": [
            {"title": "X", "snippet": "y", "source": "pubmed", "published_year": 2022, "score": 0.5}
        ]
    }
    bundle = asyncio.run(retriever.retrieve(extracted, session=_TextSession(rows)))
    assert bundle.literature[0].title == "X"
