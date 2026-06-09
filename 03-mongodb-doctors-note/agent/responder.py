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

import asyncio
import datetime as dt
import json
import re
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field, model_validator

from extractor import ExtractedReport
from prompts import DISCLAIMER_LONG, SYNTHESIS_SYSTEM_PROMPT
from retriever import RetrievalBundle, RetrievedDoc
from vertex_ai import get_client, get_embedding_model, get_gemini_model


# ---------------------------------------------------------------------------
# Diagnostic-language gate
#
# The Pydantic schema enforces structural invariants (disclaimer present,
# follow-up references the clinician). It cannot see *drift inside the prose*
# — a model that, despite the system prompt, writes "you have cancer" in the
# translation field. These high-precision patterns catch that class of
# violation. On a hit we discard the generated prose and fall back to the
# safe, disclaimer-bearing response rather than ship diagnostic language.
#
# Patterns are deliberately narrow (they require a medical object) so legal
# phrasings like "your report describes...", "this finding is associated
# with...", or "you may want to ask your clinician whether..." never trip.
# ---------------------------------------------------------------------------

_DIAGNOSIS_OBJECT = (
    r"cancer|carcinoma|malignancy|malignant|tumou?r|benign|nodule|mass|"
    r"lesion|disease|anemia|anaemia|infection|condition"
)

_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "you have a thyroid nodule", "you do not have cancer", etc.
    re.compile(
        r"\byou\s+(?:have|have got|probably have|likely have|most likely have|"
        r"definitely have|do not have|don'?t have)\b(?:\s+\w+){0,3}?\s+"
        rf"(?:{_DIAGNOSIS_OBJECT})\b",
        re.IGNORECASE,
    ),
    # "the diagnosis is ...", "the diagnosis could be ..."
    re.compile(
        r"\bthe\s+diagnosis\s+(?:is|was|will be|could be|may be|is likely|"
        r"appears to be)\b",
        re.IGNORECASE,
    ),
    # "you are diagnosed with ...", "you're suffering from ..."
    re.compile(
        r"\byou(?:\s+are|'re)\s+(?:diagnosed with|suffering from|positive for)\b",
        re.IGNORECASE,
    ),
    # "this is cancer", "this is benign", "this looks like a malignancy"
    re.compile(
        r"\bthis\s+(?:is|looks like|appears to be|is likely)\s+(?:a\s+|an\s+)?"
        rf"(?:{_DIAGNOSIS_OBJECT})\b",
        re.IGNORECASE,
    ),
)


def find_diagnostic_violation(decoded: "DecodedReport") -> str | None:
    """Return the first diagnostic phrase found in the prose, or None.

    Scans the free-text fields most likely to attract diagnostic drift.
    Emergency-shaped responses are exempt: they intentionally carry the
    fixed REFUSAL_EMERGENCY text, not generated prose.
    """

    if decoded.is_emergency_shaped:
        return None

    prose = " ".join(
        [
            decoded.translation,
            decoded.what_this_means,
            decoded.statistical_context,
            decoded.likely_followup,
            *decoded.questions_to_ask,
        ]
    )
    for pattern in _BANNED_PATTERNS:
        match = pattern.search(prose)
        if match:
            return match.group(0)
    return None


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
    """Produce the final structured response with a safe fallback."""

    _ = SYNTHESIS_SYSTEM_PROMPT  # imported so missing prompt fails at import
    try:
        response = await asyncio.to_thread(
            _generate_response,
            extracted=extracted,
            bundle=bundle,
        )
        decoded = DecodedReport.model_validate_json(response.text or "")

        violation = find_diagnostic_violation(decoded)
        if violation is not None:
            # The model produced diagnostic prose despite the system prompt.
            # Do not ship it: return the safe, disclaimer-bearing fallback and
            # record what tripped the gate for observability.
            fallback = _fallback_response(
                bundle, error=ValueError(f"diagnostic language: {violation!r}")
            )
            fallback.metadata["safety_filtered"] = True
            fallback.metadata["safety_match"] = violation
            return fallback

        decoded.metadata = {
            **decoded.metadata,
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "gemini_model": get_gemini_model(),
            "embedding_model": get_embedding_model(),
            "stub": False,
            "safety_filtered": False,
        }
        return decoded
    except Exception as exc:
        return _fallback_response(bundle, error=exc)


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


def _generate_response(
    *,
    extracted: ExtractedReport,
    bundle: RetrievalBundle,
):
    """Synchronous SDK call used from :func:`respond`."""

    payload = json.dumps(
        {
            "extracted_report": extracted.model_dump(mode="json"),
            "retrieval_bundle": _bundle_to_dict(bundle),
        },
        indent=2,
    )
    config = types.GenerateContentConfig(
        system_instruction=SYNTHESIS_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.2,
    )
    return get_client().models.generate_content(
        model=get_gemini_model(),
        contents=payload,
        config=config,
    )


def _bundle_to_dict(bundle: RetrievalBundle) -> dict[str, list[dict[str, Any]]]:
    """Convert retrieval bundle dataclasses into JSON-serializable payloads."""

    return {
        "literature": [doc.__dict__ for doc in bundle.literature],
        "guidelines": [doc.__dict__ for doc in bundle.guidelines],
        "forum_posts": [doc.__dict__ for doc in bundle.forum_posts],
    }


def _fallback_response(bundle: RetrievalBundle, *, error: Exception) -> DecodedReport:
    """Return a conservative response when Gemini generation fails."""

    sources = _flatten_sources(bundle)
    return DecodedReport(
        translation=(
            "Your report describes a finding that should be reviewed in context "
            "with your clinician. I could not safely generate a more specific "
            "plain-language explanation from the current model response."
        ),
        what_this_means=(
            "The safest next step is to use the report language and the cited "
            "sources below as preparation for your appointment, rather than "
            "treating this response as a diagnosis."
        ),
        statistical_context=(
            "I do not have a reliable statistic to provide from the current "
            "response path. Please use the cited sources and confirm the "
            "relevant numbers with your clinician."
        ),
        questions_to_ask=[
            "Can you walk me through what the key terms in this report mean?",
            "What follow-up, if any, do you expect based on this report?",
            "Which part of this report matters most for my next appointment?",
        ],
        likely_followup=(
            "A follow-up discussion with your clinician is likely the right "
            "next step so the report can be interpreted with your full history."
        ),
        disclaimer=DISCLAIMER_LONG,
        sources=sources,
        is_emergency_shaped=False,
        metadata={
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "gemini_model": get_gemini_model(),
            "embedding_model": get_embedding_model(),
            "stub": False,
            "fallback": True,
            "error_type": type(error).__name__,
        },
    )
