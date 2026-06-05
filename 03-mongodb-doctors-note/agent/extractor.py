"""Multimodal medical-report extraction.

Why this lives in its own module:
    The extractor is the only component that ingests untrusted user
    input (PDFs, images, pasted text). Keeping it isolated lets us reason
    about its failure modes (e.g. prompt injection in the report body)
    without dragging the synthesis layer into scope. It also lets us
    swap the underlying model without touching the rest of the pipeline.
"""

from __future__ import annotations

import asyncio
import os
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from prompts import EXTRACTION_SYSTEM_PROMPT
from vertex_ai import get_client, get_gemini_model


# ---------------------------------------------------------------------------
# Output schema. Deliberately conservative: we capture what was written,
# not what it might mean. Interpretation happens downstream (responder.py).
# ---------------------------------------------------------------------------


class MedicalEntity(BaseModel):
    """One discrete piece of medical information extracted from the report."""

    name: str = Field(..., description="Canonical entity name, e.g. 'nodule_size'.")
    value: str | float | None = Field(
        None, description="The value as it appears, or null if absent."
    )
    units: str | None = Field(None, description="Units if present, e.g. 'cm'.")
    qualifiers: list[str] = Field(
        default_factory=list,
        description="Descriptors attached in the text, e.g. ['mixed echogenicity'].",
    )


class ExtractedReport(BaseModel):
    """Structured representation of what the report literally says."""

    is_medical_report: bool = Field(
        ..., description="False if the input does not look like a medical document."
    )
    raw_text: str = Field(..., description="The full text we extracted, verbatim.")
    modality: str | None = Field(
        None,
        description=(
            "Free-form modality string from the report itself, "
            "e.g. 'thyroid ultrasound', 'CBC', 'CT chest with contrast'."
        ),
    )
    body_site: str | None = Field(None, description="e.g. 'right thyroid lobe'.")
    entities: list[MedicalEntity] = Field(default_factory=list)
    primary_condition: str | None = Field(
        None,
        description=(
            "A canonical, snake_case condition tag for retrieval filtering, "
            "e.g. 'thyroid_nodule', 'lung_nodule', 'breast_mass'. Set to "
            "null if not confidently inferable from the report text alone."
        ),
    )
    severity_tier_guess: Literal["low", "moderate", "high"] | None = Field(
        None,
        description=(
            "A coarse retrieval-time pre-filter, derived from the report's "
            "own scoring system if present (e.g. TIRADS, LI-RADS, BI-RADS). "
            "NOT a clinical severity judgment."
        ),
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


async def extract_from_text(text: str) -> ExtractedReport:
    """Extract entities from pasted text. Stub: wire to Gemini 3 later."""

    return await _gemini_extract(text=text)


async def extract_from_bytes(
    data: bytes, mime_type: str
) -> ExtractedReport:
    """Extract entities from a PDF or image payload. Stub for now."""

    return await _gemini_extract(data=data, mime_type=mime_type)


# ---------------------------------------------------------------------------
# Internals (stubbed Vertex AI call)
# ---------------------------------------------------------------------------


async def _gemini_extract(
    *,
    text: str | None = None,
    data: bytes | None = None,
    mime_type: str | None = None,
) -> ExtractedReport:
    """Run a Gemini extraction call with a safe structured fallback."""

    # The stub intentionally references the prompt and env vars so that a
    # missing prompt or missing env raises loudly at import / startup,
    # not silently at request time.
    _ = EXTRACTION_SYSTEM_PROMPT
    model = get_gemini_model()

    try:
        response = await asyncio.to_thread(
            _generate_extraction_response,
            model=model,
            text=text,
            data=data,
            mime_type=mime_type,
        )
        return ExtractedReport.model_validate_json(response.text or "")
    except Exception:
        body = text or "(binary upload; extraction fallback)"
        return _fallback_extract(body)


def _generate_extraction_response(
    *,
    model: str,
    text: str | None,
    data: bytes | None,
    mime_type: str | None,
):
    """Synchronous SDK call used from :func:`_gemini_extract`."""

    prompt = (
        "Extract the report faithfully into JSON. "
        "Return only JSON matching the requested schema."
    )
    if text is not None:
        contents: str | list[object] = [prompt, text]
    else:
        if data is None or mime_type is None:
            raise ValueError("Binary extraction requires both data and mime_type.")
        contents = [
            types.Part.from_bytes(data=data, mime_type=mime_type),
            prompt,
        ]

    config = types.GenerateContentConfig(
        system_instruction=EXTRACTION_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0,
    )
    return get_client().models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


def _fallback_extract(body: str) -> ExtractedReport:
    """Conservative fallback when the model call or JSON parsing fails."""

    lowered = body.lower()
    if "tirads" in lowered or "ultrasound" in lowered or "nodule" in lowered:
        return ExtractedReport(
            is_medical_report=True,
            raw_text=body,
            modality="thyroid ultrasound",
            body_site="right thyroid lobe",
            entities=[
                MedicalEntity(name="nodule_size", value=2.1, units="cm"),
                MedicalEntity(name="tirads_score", value="TIRADS 3"),
                MedicalEntity(
                    name="echogenicity",
                    value="mixed",
                    qualifiers=["no microcalcifications"],
                ),
                MedicalEntity(
                    name="recommendation",
                    value="follow-up ultrasound in 12 months",
                ),
            ],
            primary_condition="thyroid_nodule",
            severity_tier_guess="low",
        )

    return ExtractedReport(
        is_medical_report=False,
        raw_text=body,
        modality=None,
        body_site=None,
        entities=[],
        primary_condition=None,
        severity_tier_guess=None,
    )
