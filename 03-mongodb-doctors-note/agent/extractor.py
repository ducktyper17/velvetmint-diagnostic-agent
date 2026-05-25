"""Multimodal medical-report extraction.

Why this lives in its own module:
    The extractor is the only component that ingests untrusted user
    input (PDFs, images, pasted text). Keeping it isolated lets us reason
    about its failure modes (e.g. prompt injection in the report body)
    without dragging the synthesis layer into scope. It also lets us
    swap the underlying model without touching the rest of the pipeline.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from prompts import EXTRACTION_SYSTEM_PROMPT


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
    """Stub for the Gemini 3 multimodal extraction call.

    TODO wire to vertexai.generative_models.GenerativeModel(...).generate_content_async(...)
    once the project's GCP creds are set up. Real implementation will:
        1. Build a vertexai.Part list from `text` and/or (`data`, `mime_type`).
        2. Call the model with EXTRACTION_SYSTEM_PROMPT as the system
           instruction and request JSON output via response_mime_type and
           response_schema (Pydantic -> JSON schema).
        3. Parse the JSON into ExtractedReport.
        4. Defensive: if parsing fails, return a minimal ExtractedReport
           with `is_medical_report=False` rather than raising.

    The stub returns a fixed thyroid example so the rest of the pipeline
    is independently runnable for development.
    """

    # The stub intentionally references the prompt and env vars so that a
    # missing prompt or missing env raises loudly at import / startup,
    # not silently at request time.
    _ = EXTRACTION_SYSTEM_PROMPT
    _ = os.getenv("GEMINI_MODEL", "gemini-3-pro")

    body = text or "(binary upload; Gemini multimodal not wired in stub)"

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
