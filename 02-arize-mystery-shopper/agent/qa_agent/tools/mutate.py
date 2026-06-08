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

Constraints (the diff must be auditable and safety-bounded):

1. You may remove one or more lines that begin with "# FLAW(" — these are
   pre-tagged known-bad rules that should be replaced. Remove ONLY the
   FLAW lines whose label is directly relevant to the cluster you are
   addressing. List each removed line VERBATIM in `removed_flaw_lines`.

2. You may append 1-2 sentences of new instruction at the end.

3. You may NOT edit, reorder, or rewrite any line that is not a
   "# FLAW(...)" line. Any other change is rejected.

4. The appended sentence(s) must address the cluster's root cause
   concretely (e.g. "never invent policies that are not in your tools",
   not "be more careful").

5. Address one cluster per cycle. Pick the strongest signal.

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
  "removed_flaw_lines": ["<exact line text>", ...],
  "appended": "<the exact text you are appending, or empty string if removal-only>",
  "new_prompt": "<the full updated prompt>"
}}

`removed_flaw_lines` may be an empty list (append-only) or a list of one or
more verbatim lines starting with "# FLAW(". Output no other text.
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
    removed_raw = result.get("removed_flaw_lines") or []
    removed_lines: list[str] = (
        [str(line).strip() for line in removed_raw if str(line).strip()]
        if isinstance(removed_raw, list)
        else []
    )

    if not new_prompt:
        return {"error": "mutation response missing 'new_prompt'."}
    if not appended and not removed_lines:
        return {"error": "mutation must either remove a FLAW line or append text."}

    # Validate: every removed line must start with "# FLAW(" so the agent
    # cannot strip arbitrary rules under cover of the cluster narrative.
    for line in removed_lines:
        stripped = line.lstrip("- ").strip()
        if not stripped.startswith("# FLAW("):
            return {
                "error": (
                    f"removed line must start with '# FLAW(' (after bullet/whitespace); "
                    f"got: {line!r}"
                )
            }

    # Reconstruct the expected new prompt from current minus removed plus
    # appended. If Gemini's `new_prompt` doesn't match within whitespace
    # tolerance, coerce to the reconstructed version — the structural diff
    # is what we audit, not the model's free-form text.
    reconstructed = _apply_diff(
        current=current_prompt,
        removed_lines=removed_lines,
        appended=appended,
    )
    if _normalize(new_prompt) != _normalize(reconstructed):
        _log.warning(
            "mutation new_prompt diverges from reconstructed diff; coercing"
        )
        new_prompt = reconstructed

    # Cap the appended text length so diffs stay legible.
    if len(appended) > 600:
        return {"error": f"appended rule too long ({len(appended)} chars); reject."}

    return {
        "rationale": rationale or "(model returned no rationale)",
        "removed_flaw_lines": removed_lines,
        "appended": appended,
        "new_prompt": new_prompt,
        "parent_prompt_hash": _stable_hash(current_prompt),
    }


def _apply_diff(
    *,
    current: str,
    removed_lines: list[str],
    appended: str,
) -> str:
    """Apply a remove-FLAW-lines-then-append diff to the current prompt.

    Matching is tolerant to leading bullet markers and whitespace — the SUT
    prompt's FLAW lines look like ``- # FLAW(...)`` (bulleted) but the
    mutation model sometimes returns the unbulleted form ``# FLAW(...)`` in
    `removed_flaw_lines`. We normalize both sides before comparing.
    """

    removed_strip = {_normalize_for_match(line) for line in removed_lines}
    keep: list[str] = []
    for line in current.split("\n"):
        if _normalize_for_match(line) in removed_strip:
            continue
        keep.append(line)
    rebuilt = "\n".join(keep).rstrip()
    if appended:
        rebuilt = rebuilt + "\n" + appended.strip() + "\n"
    return rebuilt


def _normalize_for_match(line: str) -> str:
    """Strip leading bullet markers and whitespace so line-comparison is forgiving.

    The SUT prompt uses ``- # FLAW(...)`` (markdown bullet). Gemini sometimes
    drops the bullet when reporting `removed_flaw_lines`. This normalizer
    aligns both sides.
    """

    s = line.strip()
    while s.startswith("- "):
        s = s[2:].strip()
    return s


def _normalize(text: str) -> str:
    """Collapse whitespace differences for diff comparisons."""

    return "\n".join(line.rstrip() for line in text.strip().split("\n"))


def _stable_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


__all__ = ["mutate_sut_prompt"]
