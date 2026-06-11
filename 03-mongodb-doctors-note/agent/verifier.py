"""Self-verification: does the draft explanation actually hold up?

Why this module exists:
    A retrieval-augmented explainer can still drift — cite a statistic that
    isn't in any retrieved source, or slip into diagnostic phrasing. This
    module is the agent's *reflection* step: it inspects its own draft
    against the evidence it retrieved and decides whether to accept it or
    send it back for one revision. That self-critique loop is what makes
    this an agent rather than a one-shot RAG pipeline.

Two checks, in order of severity:
    1. Diagnostic-language gate (reuses responder.find_diagnostic_violation):
       a hard safety stop.
    2. Statistical grounding: every percentage the draft asserts must appear
       in a retrieved source snippet. When a Gemini verifier is available we
       use it for nuance; we always fall back to a deterministic
       percent-matching check so the loop works with or without a model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from prompts import VERIFIER_SYSTEM_PROMPT
from responder import DecodedReport, find_diagnostic_violation
from retriever import RetrievalBundle
from vertex_ai import get_client, get_gemini_model


@dataclass
class VerificationResult:
    """Outcome of one verification pass over a draft."""

    grounded: bool
    issues: list[str]
    method: str  # "model" | "heuristic"


_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", re.IGNORECASE)


def _percents(text: str) -> set[str]:
    """Normalize percentages to bare numbers for comparison ('5%', '5 percent' -> '5')."""

    return {m.group(1) for m in _PERCENT_RE.finditer(text)}


def _bundle_text(bundle: RetrievalBundle) -> str:
    parts: list[str] = []
    for group in (bundle.literature, bundle.guidelines, bundle.forum_posts):
        for doc in group:
            parts.append(f"{doc.title} {doc.snippet}")
    return " ".join(parts)


def _heuristic_grounding(decoded: DecodedReport, bundle: RetrievalBundle) -> list[str]:
    """Deterministic grounding check: claimed percentages must appear in sources.

    Conservative by design: we only flag a *specific* percentage the draft
    asserts that is absent from every retrieved snippet. A draft that says
    "I do not have a statistic for this in my sources" makes no percentage
    claim and therefore cannot fail this check.
    """

    claimed = _percents(decoded.statistical_context)
    if not claimed:
        return []
    supported = _percents(_bundle_text(bundle))
    ungrounded = sorted(claimed - supported)
    if ungrounded:
        joined = ", ".join(f"{n}%" for n in ungrounded)
        return [
            f"statistical_context cites {joined}, which does not appear in any "
            "retrieved source. Either cite a source that contains it or say "
            "you do not have a statistic for this."
        ]
    return []


def _model_grounding(decoded: DecodedReport, bundle: RetrievalBundle) -> list[str] | None:
    """Ask Gemini to judge grounding. Returns issues, or None if unavailable."""

    payload = json.dumps(
        {
            "draft": {
                "translation": decoded.translation,
                "what_this_means": decoded.what_this_means,
                "statistical_context": decoded.statistical_context,
                "likely_followup": decoded.likely_followup,
                "questions_to_ask": decoded.questions_to_ask,
            },
            "sources": [
                {"title": d.title, "snippet": d.snippet, "source": d.source}
                for group in (bundle.literature, bundle.guidelines, bundle.forum_posts)
                for d in group
            ],
        },
        indent=2,
    )
    from google.genai import types  # local import keeps module import cheap

    config = types.GenerateContentConfig(
        system_instruction=VERIFIER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0,
    )
    response = get_client().models.generate_content(
        model=get_gemini_model(),
        contents=payload,
        config=config,
    )
    data = json.loads(response.text or "{}")
    issues = data.get("issues") or []
    return [str(i) for i in issues if str(i).strip()]


def verify_draft(decoded: DecodedReport, bundle: RetrievalBundle) -> VerificationResult:
    """Run the agent's self-check over a draft and return a verdict.

    Diagnostic language is always a hard failure. Grounding is judged by the
    Gemini verifier when reachable, otherwise by the deterministic percent
    check. The two issue lists are merged.
    """

    issues: list[str] = []

    violation = find_diagnostic_violation(decoded)
    if violation is not None:
        issues.append(f"diagnostic language detected: {violation!r}. Rephrase to describe the report, not diagnose.")

    method = "heuristic"
    grounding_issues: list[str] | None = None
    try:
        grounding_issues = _model_grounding(decoded, bundle)
        method = "model"
    except Exception:
        grounding_issues = None

    if grounding_issues is None:
        grounding_issues = _heuristic_grounding(decoded, bundle)

    issues.extend(grounding_issues)
    return VerificationResult(grounded=not issues, issues=issues, method=method)
