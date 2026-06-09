"""Tests for the response contract and the diagnostic-language gate.

The product's safety story rests on two layers:
  1. Pydantic schema validators (structural: disclaimer present, follow-up
     references the clinician).
  2. find_diagnostic_violation (prose: catches diagnostic language that
     drifts past the system prompt).
Both are tested here without any model or network call.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from responder import DecodedReport, _fallback_response, find_diagnostic_violation
from retriever import RetrievalBundle


def _valid_report(**overrides) -> DecodedReport:
    base = dict(
        translation="Your report describes a 2.1 cm thyroid nodule. TIRADS 3 means mildly suspicious.",
        what_this_means="Your report recommends a follow-up ultrasound in 12 months.",
        statistical_context="In published series, this finding is associated with ~5% malignancy risk.",
        questions_to_ask=[
            "Should we baseline TSH before the follow-up scan?",
            "If the nodule grows by the 12-month scan, what is the next step?",
            "Does any feature change the 12-month timeline?",
        ],
        likely_followup="A follow-up discussion with your clinician is likely the right next step.",
        disclaimer="LEGAL DISCLAIMER TEXT",
    )
    base.update(overrides)
    return DecodedReport(**base)


# --- Schema validators -----------------------------------------------------


def test_empty_disclaimer_is_rejected():
    with pytest.raises(ValidationError):
        _valid_report(disclaimer="   ")


def test_followup_must_reference_clinician():
    with pytest.raises(ValidationError):
        _valid_report(likely_followup="A follow-up is likely the right next step.")


def test_questions_must_be_exactly_three():
    with pytest.raises(ValidationError):
        _valid_report(questions_to_ask=["only", "two"])


# --- Diagnostic-language gate ----------------------------------------------


def test_clean_report_has_no_violation():
    assert find_diagnostic_violation(_valid_report()) is None


def test_fallback_response_does_not_self_trip():
    empty = RetrievalBundle(literature=[], guidelines=[], forum_posts=[])
    fallback = _fallback_response(empty, error=ValueError("x"))
    assert find_diagnostic_violation(fallback) is None


@pytest.mark.parametrize(
    "field,text",
    [
        ("translation", "You have cancer in your thyroid."),
        ("what_this_means", "The diagnosis is a malignant tumor."),
        ("statistical_context", "You do not have cancer based on this."),
        ("translation", "This is a malignancy that needs treatment."),
        ("what_this_means", "You are diagnosed with thyroid disease."),
    ],
)
def test_diagnostic_phrases_are_caught(field, text):
    assert find_diagnostic_violation(_valid_report(**{field: text})) is not None


@pytest.mark.parametrize(
    "field,text",
    [
        ("what_this_means", "You have questions to bring to your clinician."),
        ("translation", "This is a standardized radiology score, not a diagnosis."),
        (
            "likely_followup",
            "You may want to ask your clinician whether labs help. Discuss with your clinician.",
        ),
    ],
)
def test_legitimate_phrasings_are_not_flagged(field, text):
    assert find_diagnostic_violation(_valid_report(**{field: text})) is None
