"""``cluster_failures`` — group judge rationales into 1-3 failure modes.

Why this exists as a tool and not pure prompt:

Gemini 2.5 Pro can absolutely cluster strings by hand in its system prompt.
Exposing this as a callable tool buys us three things:

1. **Determinism for the demo.** The tool always returns the same shape:
   ``{clusters: [{name, count, root_cause_hypothesis, member_session_ids}]}``.
   That fixes the rest of the loop's contract.
2. **A traceable span.** The clustering step becomes a Phoenix span,
   inspectable in the trace tree like every other step.
3. **A natural retry point.** If the clustering output is malformed, we
   retry just this step rather than re-running the audit.

Implementation is a single Gemini 2.5 Flash call with a tight JSON-schema
prompt. We use Flash here (not Pro) because clustering 11 rationales is
shallow reasoning and Flash is ~5x cheaper.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from qa_agent.gemini_client import generate_json

_log = logging.getLogger(__name__)

_CLUSTER_MODEL = os.environ.get("CLUSTER_MODEL", "gemini-2.5-flash")
_VALID_DIMS = {"empathy", "accuracy", "escalation", "bias", "hallucination", "brand_voice"}

_CLUSTER_PROMPT = """\
You are a triage assistant. Below are JSON-encoded judge rationales for
failing scenarios run against a customer-support AI. Group them into 1-3
named failure clusters. Each cluster is a single coherent failure mode.

For each cluster, output:
  - name: a short kebab-case identifier (e.g. "fabricated-policies").
  - count: integer, the number of failures in the cluster.
  - member_session_ids: the session_ids of the failures in this cluster.
  - root_cause_hypothesis: ONE sentence naming what the agent is doing wrong.
  - dimensions_affected: list of judge dimensions ("empathy", "accuracy",
    "escalation", "bias", "hallucination", "brand_voice") that this
    cluster's failures share.

Use only the rationales as evidence. Do not invent causes that are not
visible in the text.

Rationales:
{rationales}

Respond as a JSON object: {{"clusters": [<cluster objects>]}}. No other text.
"""


def cluster_failures(rationales: list[dict[str, Any]]) -> dict[str, Any]:
    """Cluster failing-scenario rationales into 1-3 failure modes.

    Args:
        rationales: a list of dicts; each dict should contain at least the
            keys ``session_id``, ``dimension``, ``score``, ``rationale``.
            Extra keys are ignored.

    Returns:
        A dict ``{clusters: [...]}``. See the prompt above for the cluster
        schema.
    """

    if not rationales:
        return {"clusters": []}

    rendered = json.dumps(
        [
            {
                "session_id": r.get("session_id", ""),
                "dimension": r.get("dimension", ""),
                "score": r.get("score", 0.0),
                "rationale": r.get("rationale", ""),
            }
            for r in rationales
        ],
        indent=2,
    )

    try:
        result = generate_json(
            model=_CLUSTER_MODEL,
            prompt=_CLUSTER_PROMPT.format(rationales=rendered),
            temperature=0.1,
        )
    except Exception as exc:
        _log.error("cluster Gemini call failed, falling back to group-by-dim: %r", exc)
        return _fallback_cluster(rationales)

    clusters = result.get("clusters") or []
    if not isinstance(clusters, list):
        _log.warning("cluster response 'clusters' not a list; falling back")
        return _fallback_cluster(rationales)

    return {"clusters": [_normalize_cluster(c) for c in clusters[:3]]}


def _normalize_cluster(c: dict[str, Any]) -> dict[str, Any]:
    """Coerce a model-emitted cluster dict into the required shape."""

    members = c.get("member_session_ids") or []
    if not isinstance(members, list):
        members = []
    dims = c.get("dimensions_affected") or []
    if not isinstance(dims, list):
        dims = []
    dims = [d for d in dims if d in _VALID_DIMS]
    return {
        "name": str(c.get("name", "unnamed-cluster")).strip() or "unnamed-cluster",
        "count": int(c.get("count", len(members))),
        "member_session_ids": [str(m) for m in members],
        "root_cause_hypothesis": str(c.get("root_cause_hypothesis", "")).strip(),
        "dimensions_affected": dims,
    }


def _fallback_cluster(rationales: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic group-by-dimension fallback.

    Used when the Gemini cluster call fails — the demo must still run
    end-to-end. The QA agent's report will note that clustering fell back,
    which is more honest than pretending the model worked.
    """

    by_dim: dict[str, list[dict[str, Any]]] = {}
    for r in rationales:
        by_dim.setdefault(r.get("dimension", "unknown"), []).append(r)
    clusters: list[dict[str, Any]] = []
    for dim, items in by_dim.items():
        clusters.append(
            {
                "name": f"{dim}-failures",
                "count": len(items),
                "member_session_ids": [r.get("session_id", "") for r in items],
                "root_cause_hypothesis": (
                    f"[fallback] SUT scored poorly on {dim} across {len(items)} scenarios."
                ),
                "dimensions_affected": [dim],
            }
        )
    clusters.sort(key=lambda c: c["count"], reverse=True)
    return {"clusters": clusters[:3]}


__all__ = ["cluster_failures"]
