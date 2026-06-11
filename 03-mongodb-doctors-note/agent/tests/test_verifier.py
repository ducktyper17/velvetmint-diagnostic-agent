"""Tests for the self-verification step (deterministic / heuristic path)."""

from __future__ import annotations

import verifier
from responder import DecodedReport
from retriever import RetrievedDoc, RetrievalBundle


def _report(stat: str, **overrides) -> DecodedReport:
    base = dict(
        translation="Your report describes a 2.1 cm thyroid nodule, TIRADS 3.",
        what_this_means="Your report recommends follow-up ultrasound in 12 months.",
        statistical_context=stat,
        questions_to_ask=["Q1?", "Q2?", "Q3?"],
        likely_followup="Discuss the timeline with your clinician.",
        disclaimer="DISCLAIMER",
    )
    base.update(overrides)
    return DecodedReport(**base)


def _bundle_with(snippet: str) -> RetrievalBundle:
    doc = RetrievedDoc(
        collection="literature",
        title="TIRADS 3 meta-analysis",
        snippet=snippet,
        source="pubmed",
        url=None,
        published_year=2023,
        score=0.8,
    )
    return RetrievalBundle(literature=[doc], guidelines=[], forum_posts=[])


def _force_heuristic(monkeypatch):
    # Make the model path unavailable so we exercise the deterministic check.
    def boom(*a, **k):
        raise RuntimeError("no model in tests")

    monkeypatch.setattr(verifier, "_model_grounding", boom)


def test_grounded_when_percent_appears_in_sources(monkeypatch):
    _force_heuristic(monkeypatch)
    report = _report("In published series this finding carries about 5% malignancy risk.")
    bundle = _bundle_with("pooled malignancy risk of approximately 5% across studies")
    result = verifier.verify_draft(report, bundle)
    assert result.grounded is True
    assert result.method == "heuristic"


def test_ungrounded_percent_is_flagged(monkeypatch):
    _force_heuristic(monkeypatch)
    report = _report("This finding carries a 40% malignancy risk.")
    bundle = _bundle_with("pooled malignancy risk of approximately 5%")
    result = verifier.verify_draft(report, bundle)
    assert result.grounded is False
    assert any("40%" in issue for issue in result.issues)


def test_no_statistic_claim_cannot_fail_grounding(monkeypatch):
    _force_heuristic(monkeypatch)
    report = _report("I do not have a statistic for this in my sources.")
    bundle = _bundle_with("some unrelated text with no percentages")
    result = verifier.verify_draft(report, bundle)
    assert result.grounded is True


def test_diagnostic_language_is_always_flagged(monkeypatch):
    _force_heuristic(monkeypatch)
    report = _report(
        "I do not have a statistic for this in my sources.",
        translation="You have cancer.",
    )
    bundle = _bundle_with("anything")
    result = verifier.verify_draft(report, bundle)
    assert result.grounded is False
    assert any("diagnostic language" in issue for issue in result.issues)
