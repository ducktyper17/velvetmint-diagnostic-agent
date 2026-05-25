"""Final synthesis: ExtractedReport + RetrievalBundle -> DecodedReport.

Why this lives in its own module:
    The Pydantic response schema is the product's contract with the
    caller. Defining it here, next to the synthesis prompt, keeps the
    schema honest with the prompt: if you add a field here you must
    update the prompt (and vice versa). The schema also doubles as the
    structured-output schema we hand to Gemini, so the model returns
    JSON that validates directly.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from pydantic import BaseModel, Field, model_validator

from extractor import ExtractedReport
from prompts import DISCLAIMER_LONG, SYNTHESIS_SYSTEM_PROMPT
from retriever import RetrievalBundle, RetrievedDoc


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class SourceCitation(BaseModel):
    """One source the responder cited."""

    source: str = Field(..., description="Stable source ID, e.g. 'pubmed', 'acr_tirads_2017'.")
    title: str
    url: str | None = None
    collection: str = Field(..., description="Which Atlas collection it came from.")


class DecodedReport(BaseModel):
    """The structured response returned by `/decode`.

    Every field except `sources` and `is_emergency_shaped` is required to
    be non-empty in a normal response. The disclaimer is enforced by a
    model validator below: if it is missing or empty, validation fails
    and FastAPI returns 500. This is the failsafe behind the prompt rule.
    """

    translation: str = Field(
        ..., description="Plain-language statement of what the report says."
    )
    what_this_means: str = Field(
        ..., description="What the report's recommendations / next steps mean."
    )
    statistical_context: str = Field(
        ...,
        description=(
            "Population-level base rate for this finding, citing the "
            "retrieved literature. May say 'I do not have a statistic for "
            "this in my sources' rather than fabricate."
        ),
    )
    questions_to_ask: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly three specific questions for the clinician.",
    )
    likely_followup: str = Field(
        ...,
        description=(
            "Plain-language note about whether and when a follow-up "
            "appointment is likely (per the retrieved guidelines)."
        ),
    )
    disclaimer: str = Field(
        ..., description="Long-form disclaimer, verbatim from LEGAL-DISCLAIMER.md."
    )
    sources: list[SourceCitation] = Field(default_factory=list)
    is_emergency_shaped: bool = Field(
        False,
        description=(
            "True if the report or extracted entities suggest an emergency. "
            "When true, the translation field carries REFUSAL_EMERGENCY and "
            "the other content fields are repeated boilerplate."
        ),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _disclaimer_must_be_populated(self) -> "DecodedReport":
        """Failsafe: empty disclaimer must surface as a server error.

        This is the second line of defense behind the system prompt.
        Prompts can fail; schema validators do not.
        """

        if not self.disclaimer or not self.disclaimer.strip():
            raise ValueError(
                "DecodedReport.disclaimer is required and must be non-empty. "
                "Refer to LEGAL-DISCLAIMER.md."
            )
        return self

    @model_validator(mode="after")
    def _followup_must_reference_clinician(self) -> "DecodedReport":
        """Enforce the prompt rule that the follow-up mentions the clinician.

        Keeps the response from drifting toward "you should..." language
        in the field most likely to attract it.
        """

        if "clinician" not in self.likely_followup.lower() and not self.is_emergency_shaped:
            raise ValueError(
                "DecodedReport.likely_followup must explicitly reference the "
                "clinician (e.g. 'with your clinician')."
            )
        return self


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


async def respond(
    extracted: ExtractedReport, bundle: RetrievalBundle
) -> DecodedReport:
    """Produce the final structured response.

    Stub: returns a deterministic example so the API and validators are
    exercised end-to-end without a Vertex AI call. Real implementation:
        1. Build a single user-turn message with ExtractedReport JSON and
           RetrievalBundle JSON.
        2. Call Gemini 3 with SYNTHESIS_SYSTEM_PROMPT, response_mime_type
           = application/json, response_schema = DecodedReport.
        3. Parse and validate. On validation failure, return a soft
           fallback (still with the disclaimer attached).
    """

    _ = SYNTHESIS_SYSTEM_PROMPT  # imported so missing prompt fails at import
    _ = os.getenv("GEMINI_MODEL", "gemini-3-pro")

    sources = _flatten_sources(bundle)

    return DecodedReport(
        translation=(
            "Your report describes a 2.1 cm nodule in the right lobe of your "
            "thyroid. 'TIRADS 3' is the radiologist's standardized score for "
            "how suspicious the nodule looks on ultrasound; TIRADS 3 means "
            "'mildly suspicious'."
        ),
        what_this_means=(
            "Your report's recommendation is a follow-up ultrasound in 12 "
            "months. Per the ACR 2017 TI-RADS guideline, this is the "
            "standard interval for a TIRADS 3 nodule under 2.5 cm: the "
            "intent is to watch the nodule, not to treat it now."
        ),
        statistical_context=(
            "In published meta-analyses, roughly 5 in 100 TIRADS 3 nodules "
            "of this size turn out to be malignant on biopsy; the other 95 "
            "are benign. Biopsy is not standardly performed for TIRADS 3 "
            "nodules under 2.5 cm unless other features change."
        ),
        questions_to_ask=[
            "Should we baseline labs (TSH, free T4) before the follow-up scan?",
            "If the nodule grows by the 12-month scan, what is the next step?",
            "Are there features in the scan that change the 12-month timeline?",
        ],
        likely_followup=(
            "A follow-up ultrasound in about 12 months is likely; you may "
            "want to confirm the exact timing with your clinician at your "
            "next appointment."
        ),
        disclaimer=DISCLAIMER_LONG,
        sources=sources,
        is_emergency_shaped=False,
        metadata={
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3-pro"),
            "voyage_model": os.getenv("VOYAGE_MODEL", "voyage-3-large"),
            "stub": True,
        },
    )


def _flatten_sources(bundle: RetrievalBundle) -> list[SourceCitation]:
    """Collapse the bundle into a flat citation list, deduped by URL."""

    seen: set[str] = set()
    out: list[SourceCitation] = []
    for group in (bundle.literature, bundle.guidelines, bundle.forum_posts):
        for doc in group:
            key = doc.url or f"{doc.source}::{doc.title}"
            if key in seen:
                continue
            seen.add(key)
            out.append(_to_citation(doc))
    return out


def _to_citation(doc: RetrievedDoc) -> SourceCitation:
    return SourceCitation(
        source=doc.source,
        title=doc.title,
        url=doc.url,
        collection=doc.collection,
    )
