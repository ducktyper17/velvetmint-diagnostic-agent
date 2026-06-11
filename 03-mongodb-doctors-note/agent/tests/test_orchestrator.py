"""Tests for the agent loop: draft -> verify -> revise -> finalize.

We stub retrieval, drafting, and verification so the loop's control flow is
tested deterministically without any model or network.
"""

from __future__ import annotations

import asyncio

import orchestrator
from extractor import ExtractedReport
from responder import DecodedReport
from retriever import RetrievedDoc, RetrievalBundle
from verifier import VerificationResult


def _extracted() -> ExtractedReport:
    return ExtractedReport(
        is_medical_report=True,
        raw_text="...",
        modality="thyroid ultrasound",
        body_site="right thyroid lobe",
        entities=[],
        primary_condition="thyroid_nodule",
        severity_tier_guess="low",
    )


def _bundle() -> RetrievalBundle:
    doc = RetrievedDoc("literature", "T", "snippet", "pubmed", None, 2023, 0.8)
    return RetrievalBundle(literature=[doc], guidelines=[], forum_posts=[])


def _report(translation: str) -> DecodedReport:
    return DecodedReport(
        translation=translation,
        what_this_means="means",
        statistical_context="ctx",
        questions_to_ask=["a?", "b?", "c?"],
        likely_followup="Talk to your clinician.",
        disclaimer="DISCLAIMER",
    )


def _patch_retrieve(monkeypatch):
    async def fake_retrieve(extracted, *, session=None, k=5):
        return _bundle()

    monkeypatch.setattr(orchestrator, "retrieve", fake_retrieve)


def test_clean_draft_is_accepted_without_revision(monkeypatch):
    _patch_retrieve(monkeypatch)

    async def fake_respond(extracted, bundle, *, critique=None):
        return _report("Your report describes a nodule.")

    monkeypatch.setattr(orchestrator, "respond", fake_respond)
    monkeypatch.setattr(
        orchestrator, "verify_draft", lambda d, b: VerificationResult(True, [], "heuristic")
    )

    final = asyncio.run(orchestrator.run_agent(_extracted(), session=object()))
    steps = final.metadata["agent_steps"]
    names = [s["name"] for s in steps]
    assert names == ["retrieve", "draft", "verify"]
    assert steps[-1]["status"] == "done"


def test_bad_draft_triggers_one_revision(monkeypatch):
    _patch_retrieve(monkeypatch)
    calls = {"n": 0}

    async def fake_respond(extracted, bundle, *, critique=None):
        calls["n"] += 1
        # First call is the bad draft; revision (critique set) is clean.
        return _report("revised" if critique else "bad")

    def fake_verify(decoded, bundle):
        if decoded.translation == "bad":
            return VerificationResult(False, ["statistical_context cites 40%..."], "heuristic")
        return VerificationResult(True, [], "heuristic")

    monkeypatch.setattr(orchestrator, "respond", fake_respond)
    monkeypatch.setattr(orchestrator, "verify_draft", fake_verify)

    final = asyncio.run(orchestrator.run_agent(_extracted(), session=object()))
    names = [s["name"] for s in final.metadata["agent_steps"]]
    assert names == ["retrieve", "draft", "verify", "revise"]
    assert final.metadata["agent_steps"][-1]["status"] == "revised"
    assert final.translation == "revised"
    assert calls["n"] == 2  # exactly one revision


def test_revision_that_does_not_help_keeps_original(monkeypatch):
    _patch_retrieve(monkeypatch)

    async def fake_respond(extracted, bundle, *, critique=None):
        return _report("revised" if critique else "original")

    # Revision is no better than the original (same number of issues).
    def fake_verify(decoded, bundle):
        return VerificationResult(False, ["issue one", "issue two"], "heuristic")

    monkeypatch.setattr(orchestrator, "respond", fake_respond)
    monkeypatch.setattr(orchestrator, "verify_draft", fake_verify)

    final = asyncio.run(orchestrator.run_agent(_extracted(), session=object()))
    assert final.translation == "original"  # kept the safer original
    assert final.metadata["agent_steps"][-1]["status"] == "skipped"
