"""``mutate_sut_prompt`` — propose a minimal-diff edit to the SUT system prompt.

Constraints encoded here (not just in the QA agent's instruction) so the
demo cannot accidentally produce a "rewrite the whole prompt" diff:

- The diff is **additive** in the MVP. We append a 1-2 sentence rule to the
  SUT prompt rather than rewriting earlier lines. Appending is easier to
  reason about and easier to roll back. Multi-cycle runs can stack appends.
- The new rule must reference the cluster's root cause directly. If the
  generator can't tie the rule to the cluster, the tool errors out and the
  QA agent moves to the next cluster (or stops).
- The tool returns a **diff object** plus the new full template, so the
  QA agent can show the diff in its report and the Phoenix UI can preview
  what changed.

The actual mutation call uses Gemini 2.5 Pro (the QA-side model) because
this is the most consequential reasoning step in the loop. Cost is bounded
to 1-3 calls per audit.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from qa_agent.gemini_client import generate_json

_log = logging.getLogger(__name__)

_MUTATE_MODEL = os.environ.get("MUTATE_MODEL", "gemini-2.5-pro")

_MUTATION_PROMPT = """\
You are improving a customer-support AI's system prompt. The current system
prompt is below, followed by a description of the failure cluster you must
address.

Constraints:
1. The improved prompt must add 1-2 sentences only. No edits to existing
   lines.
2. The added sentence(s) must reference the cluster's root cause concretely
   (e.g. "never invent policies that are not in your tools" rather than
   "be more careful").
3. Do not weaken any existing instruction.
4. Do not address more than one cluster. Pick the strongest signal.

Current system prompt:
---
{current_prompt}
---

Failure cluster:
  name: {cluster_name}
  count: {cluster_count}
  root_cause_hypothesis: {root_cause}
  dimensions_affected: {dimensions}

Output a JSON object: {{
  "rationale": "<one paragraph: why this edit, why now>",
  "appended": "<the exact text you are appending>",
  "new_prompt": "<the full updated prompt>"
}}

No other text.
"""


def mutate_sut_prompt(
    cluster: dict[str, Any],
    current_prompt: str,
) -> dict[str, Any]:
    """Propose a minimal-diff system-prompt edit for the chosen cluster.

    Args:
        cluster: a single cluster dict as returned by ``cluster_failures``.
        current_prompt: the SUT's current system prompt text. The QA agent
            should fetch this via Phoenix MCP ``get-latest-prompt`` before
            calling this tool.

    Returns:
        A dict with keys ``rationale``, ``appended``, ``new_prompt``,
        ``parent_prompt_hash``. The QA agent then writes ``new_prompt``
        back to Phoenix via ``upsert-prompt`` itself.
    """

    if not current_prompt.strip():
        return {"error": "current_prompt is empty; cannot mutate."}
    if not cluster or "name" not in cluster:
        return {"error": "cluster argument is missing required fields."}

    prompt = _MUTATION_PROMPT.format(
        current_prompt=current_prompt,
        cluster_name=cluster.get("name", "unknown"),
        cluster_count=cluster.get("count", 0),
        root_cause=cluster.get("root_cause_hypothesis", ""),
        dimensions=", ".join(cluster.get("dimensions_affected", []) or []),
    )

    try:
        result = generate_json(model=_MUTATE_MODEL, prompt=prompt, temperature=0.3)
    except Exception as exc:
        _log.error("mutate Gemini call failed: %r", exc)
        return {"error": f"mutation generation failed: {exc!r}"}

    rationale = str(result.get("rationale", "")).strip()
    appended = str(result.get("appended", "")).strip()
    new_prompt = str(result.get("new_prompt", "")).strip()

    if not appended or not new_prompt:
        return {"error": "mutation response missing 'appended' or 'new_prompt'."}

    # Enforce the additive-only contract. The new prompt MUST start with
    # the original verbatim (modulo trailing whitespace). If the model
    # rewrote something, reject — we cannot reason about a free-form
    # rewrite during the demo.
    if not _is_additive(current_prompt, new_prompt):
        _log.warning(
            "mutation was not additive; coercing to current_prompt + appended"
        )
        new_prompt = current_prompt.rstrip() + "\n\n" + appended + "\n"

    # Cap the appended text at 2 short paragraphs to keep the diff legible.
    if len(appended) > 600:
        return {"error": f"appended rule too long ({len(appended)} chars); reject."}

    return {
        "rationale": rationale or "(model returned no rationale)",
        "appended": appended,
        "new_prompt": new_prompt,
        "parent_prompt_hash": _stable_hash(current_prompt),
    }


def _is_additive(current: str, candidate: str) -> bool:
    """True iff candidate starts with current (trailing whitespace tolerated)."""

    return candidate.lstrip().startswith(current.strip()) or candidate.startswith(
        current.rstrip()
    )


def _stable_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


__all__ = ["mutate_sut_prompt"]
