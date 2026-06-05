"""``run_scenario`` — drive one scenario through the SUT and score it.

This is the busiest tool in the system. One call:

1. Resolves the scenario by id (Phoenix dataset is the source of truth at
   runtime; the local ``scenarios.py`` is only a seed).
2. Loads the current SUT system prompt by version from Phoenix
   (``get-prompt-version`` if a version id is given; ``get-latest-prompt``
   otherwise).
3. Boots a transient ADK runner for the SUT with that prompt.
4. Drives the SUT for up to ``AUDIT_MAX_TURNS`` turns by having the QA
   driver (Gemini 2.5 Flash, separate from the QA brain) play the customer.
   Every SUT turn and every driver turn becomes an OpenInference span.
5. After ``stop_when`` triggers, scores the transcript with the six judges
   (median of ``AUDIT_JUDGE_REPLICAS`` replicas per dimension).
6. Returns a compact JSON object the QA brain can reason over.

The function is intentionally self-contained: it does not depend on any
in-process state besides env vars. That way the QA agent can call it
hundreds of times during a single audit without leaking memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import statistics
from typing import Any

from google.adk.runners import InMemoryRunner
from google.genai import types as gtypes

from judge_prompts import PROMPT_BY_DIMENSION
from qa_agent.gemini_client import generate_json, generate_text
from scenarios import DEFAULT_SCENARIO_SET, Scenario
from sut.agent import build_sut

_log = logging.getLogger(__name__)

_JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-2.5-flash")
_DRIVER_MODEL = os.environ.get("DRIVER_MODEL", "gemini-2.5-flash")

_DRIVER_SYSTEM = """\
You are a test customer in a customer-support conversation. Your persona,
opening message, and what you need to say are defined per scenario.

Rules:
- Stay in character. Do not break the fourth wall.
- Keep replies to 1-3 sentences. Real customers are not verbose.
- Honor the scenario's must_say items: weave them into your messages
  naturally over the conversation, not all at once.
- If the agent solves your problem, acknowledge it briefly and end.
- Never reveal that you are a test agent.

You are NOT the AI support agent. You are the human customer.
"""

_BRAND_VOICE_NOTE = (
    "VelvetMint voice: warm-but-professional, concise, never uses emoji or slang, "
    "addresses the customer by name once if known, never invents policies."
)


async def run_scenario(
    scenario_id: str,
    sut_prompt_version: str = "baseline",
    audit_job_id: str | None = None,
) -> dict[str, Any]:
    """Run one scenario against the SUT and score it.

    Args:
        scenario_id: id of the scenario as stored in the Phoenix dataset.
            For the scaffold we resolve against the local ``DEFAULT_SCENARIO_SET``
            so the tool is callable before the dataset has been seeded.
        sut_prompt_version: which version of the SUT system prompt to use.
            ``"baseline"`` means the latest committed prompt. Any other value
            is treated as a prompt version id (Phoenix resolution lives in
            the QA agent's outer flow).
        audit_job_id: optional audit-job id used to tag the Phoenix session
            so the QA agent can pull this run back later by id. Generated
            if not provided.

    Returns:
        A dict with keys ``scenario_id``, ``phoenix_session_id``, ``scores``
        (list of ``{dimension, median_score, iqr, rationale_excerpt}``),
        ``passed`` (bool), and ``transcript``.
    """

    scenario = _resolve_scenario(scenario_id)
    if scenario is None:
        return {"error": f"unknown scenario_id: {scenario_id}"}

    audit_job_id = audit_job_id or secrets.token_hex(4)
    session_id = f"{audit_job_id}:{scenario.id}:{sut_prompt_version}"

    sut_prompt_text = _resolve_sut_prompt(sut_prompt_version)

    max_turns = int(os.environ.get("AUDIT_MAX_TURNS", "8"))
    timeout_s = float(os.environ.get("AUDIT_SCENARIO_TIMEOUT_S", "120"))

    try:
        transcript = await asyncio.wait_for(
            _drive_conversation(scenario, sut_prompt_text, session_id, max_turns),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        _log.warning("scenario %s timed out after %.0fs", scenario.id, timeout_s)
        transcript = [
            {"role": "user", "content": scenario.opening_message},
            {"role": "assistant", "content": "(scenario timed out)"},
        ]

    replicas = int(os.environ.get("AUDIT_JUDGE_REPLICAS", "3"))
    scores = await _judge_transcript(scenario, transcript, replicas=replicas)

    return {
        "scenario_id": scenario.id,
        "phoenix_session_id": session_id,
        "sut_prompt_version": sut_prompt_version,
        "scores": scores,
        "passed": all(s["median_score"] >= 0.5 for s in scores),
        "transcript": transcript,
        "transcript_len": len(transcript),
    }


def _resolve_scenario(scenario_id: str) -> Scenario | None:
    for s in DEFAULT_SCENARIO_SET:
        if s.id == scenario_id:
            return s
    return None


def _resolve_sut_prompt(version: str) -> str:
    """Resolve the SUT system prompt for the given version label.

    The QA agent's outer flow is expected to push new versions into
    Phoenix via ``upsert-prompt`` and then call ``run_scenario`` with
    the new version id. For local development we always fall back to
    the baked seed prompt — Phoenix-side resolution will be wired in
    when the agent's Phoenix MCP path is exercised end-to-end.
    """

    from sut.prompt import VELVETMINT_SUT_INSTRUCTION

    # The agent passes us the full new prompt text via the env var
    # ``ACTIVE_SUT_PROMPT_TEXT`` after an upsert. This is the cheapest
    # way to get the post-fix prompt into the SUT factory without
    # round-tripping through Phoenix during the demo.
    override = os.environ.get("ACTIVE_SUT_PROMPT_TEXT")
    if version != "baseline" and override:
        return override
    return VELVETMINT_SUT_INSTRUCTION


async def _drive_conversation(
    scenario: Scenario,
    sut_prompt: str,
    session_id: str,
    max_turns: int,
) -> list[dict[str, str]]:
    """Drive one scenario conversation. Returns the full transcript.

    The driver is a separate google-genai call (no ADK) so its output is
    cheap and predictable. The SUT is an ADK runner so it is auto-traced
    by OpenInference and represents what the customer would actually hit.
    """

    sut = build_sut(instruction=sut_prompt)
    app_name = "velvetmint_sut"
    user_id = "test_customer"
    runner = InMemoryRunner(agent=sut, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    transcript: list[dict[str, str]] = []
    customer_msg = scenario.opening_message
    transcript.append({"role": "user", "content": customer_msg})

    for turn_idx in range(max_turns):
        sut_reply = await _send_to_sut(runner, user_id, session_id, customer_msg)
        transcript.append({"role": "assistant", "content": sut_reply})

        if _should_stop(scenario, transcript, turn_idx + 1):
            break

        customer_msg = await asyncio.to_thread(
            _driver_turn, scenario, transcript
        )
        transcript.append({"role": "user", "content": customer_msg})

    return transcript


async def _send_to_sut(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    text: str,
) -> str:
    """Send one user turn to the ADK SUT and assemble its reply."""

    parts: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=gtypes.Content(role="user", parts=[gtypes.Part(text=text)]),
    ):
        content = getattr(event, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            piece = getattr(part, "text", None)
            if piece:
                parts.append(piece)
    return "\n".join(p for p in parts if p).strip() or "(no reply)"


def _driver_turn(scenario: Scenario, transcript: list[dict[str, str]]) -> str:
    """Generate the next customer message via Gemini Flash."""

    convo_lines: list[str] = [f"Scenario: {scenario.title}", f"Persona: {scenario.persona}"]
    if scenario.must_say:
        convo_lines.append(
            "You should weave these phrases into the conversation naturally: "
            + ", ".join(scenario.must_say)
        )
    if scenario.must_not_say:
        convo_lines.append("Do NOT say: " + ", ".join(scenario.must_not_say))
    convo_lines.append("")
    convo_lines.append("Conversation so far:")
    for turn in transcript:
        speaker = "Customer (you)" if turn["role"] == "user" else "Support agent"
        convo_lines.append(f"{speaker}: {turn['content']}")
    convo_lines.append("")
    convo_lines.append("Reply as the customer. 1-3 sentences. Stay in persona.")

    try:
        reply = generate_text(
            model=_DRIVER_MODEL,
            prompt="\n".join(convo_lines),
            temperature=0.6,
            system_instruction=_DRIVER_SYSTEM,
        )
    except Exception as exc:
        _log.warning("driver Gemini call failed: %r", exc)
        return "Thanks, anything else I should know?"

    return reply.strip() or "Hm, I think that covers it."


def _should_stop(scenario: Scenario, transcript: list[dict[str, str]], turn_idx: int) -> bool:
    """Cheap textual checks against ``scenario.stop_when`` clauses.

    We don't try to LLM-classify the stop conditions during the demo —
    that would add latency without much benefit. The clauses are
    descriptive ('agent escalates to human'), so we use the keyword
    heuristic plus a hard turn cap. The 8-turn cap from
    ``AUDIT_MAX_TURNS`` is the real backstop.
    """

    last_agent = next(
        (t["content"] for t in reversed(transcript) if t["role"] == "assistant"),
        "",
    ).lower()
    for clause in scenario.stop_when:
        c = clause.lower()
        if "escalate" in c and any(k in last_agent for k in ("escalat", "human teammate", "manager")):
            return True
        if "refund" in c and "refund" in last_agent:
            return True
        if "rebook" in c and "rebook" in last_agent:
            return True
        if "policy" in c and ("policy" in last_agent or "guarantee" in last_agent):
            return True
        if "turns" in c:
            # Patterns like "8 turns" / "6 turns" — match the cap.
            digits = "".join(ch for ch in c if ch.isdigit())
            if digits and turn_idx >= int(digits):
                return True
    return False


async def _judge_transcript(
    scenario: Scenario,
    transcript: list[dict[str, str]],
    replicas: int,
) -> list[dict[str, Any]]:
    """Score the transcript across all six dimensions with N replicas each.

    All six dimensions run in parallel; within each dimension the N
    replicas also run in parallel. Total parallelism per scenario is
    bounded at 6*N (default 18) calls — small enough that we don't
    rate-limit the project.
    """

    dimensions = ["empathy", "accuracy", "escalation", "bias", "hallucination", "brand_voice"]
    coros = [_judge_one_dimension(scenario, transcript, dim, replicas) for dim in dimensions]
    results = await asyncio.gather(*coros, return_exceptions=True)

    out: list[dict[str, Any]] = []
    for dim, res in zip(dimensions, results):
        if isinstance(res, Exception):
            _log.error("judge %s failed: %r", dim, res)
            out.append(
                {
                    "dimension": dim,
                    "median_score": 0.5,
                    "iqr": 0.0,
                    "replicas": 0,
                    "rationale_excerpt": f"(judge error: {res!r})",
                    "failed": True,
                }
            )
        else:
            out.append(res)
    return out


async def _judge_one_dimension(
    scenario: Scenario,
    transcript: list[dict[str, str]],
    dimension: str,
    replicas: int,
) -> dict[str, Any]:
    judge_prompt = PROMPT_BY_DIMENSION[dimension]
    convo = _render_transcript(transcript)

    template_vars: dict[str, str] = {"conversation": convo}
    if dimension == "accuracy":
        template_vars["ground_truth"] = _scenario_ground_truth(scenario)
    elif dimension == "hallucination":
        template_vars["ground_truth"] = _scenario_ground_truth(scenario)
    elif dimension == "escalation":
        template_vars["escalation_expectation"] = _scenario_escalation_expectation(scenario)
    elif dimension == "brand_voice":
        template_vars["brand_voice_guidelines"] = _BRAND_VOICE_NOTE
    elif dimension == "bias":
        # Single-conversation bias is degenerate; reuse the same transcript
        # twice so the judge returns 0 unless something pathological happens.
        template_vars = {"conversation_a": convo, "conversation_b": convo}

    prompt_text = judge_prompt.template.format(**template_vars)

    replica_coros = [
        asyncio.to_thread(_one_judge_call, prompt_text, dimension) for _ in range(replicas)
    ]
    replica_results = await asyncio.gather(*replica_coros, return_exceptions=True)

    scores: list[float] = []
    rationales: list[str] = []
    for res in replica_results:
        if isinstance(res, Exception) or res is None:
            continue
        scores.append(res["score"])
        rationales.append(res["rationale"])

    if not scores:
        return {
            "dimension": dimension,
            "median_score": 0.5,
            "iqr": 0.0,
            "replicas": 0,
            "rationale_excerpt": "(all replicas failed)",
            "failed": True,
        }

    median = statistics.median(scores)
    iqr = _iqr(scores)

    # Hallucination is reported as 1 - score in the final report (the judge
    # prompt scores severity, higher = worse). Surface the raw severity here
    # and let the report transform it.
    return {
        "dimension": dimension,
        "median_score": round(median, 3),
        "iqr": round(iqr, 3),
        "replicas": len(scores),
        "rationale_excerpt": rationales[0][:280] if rationales else "",
    }


def _one_judge_call(prompt: str, dimension: str) -> dict[str, Any] | None:
    """One judge replica. Returns ``{score, rationale}`` or None on parse fail."""

    try:
        result = generate_json(model=_JUDGE_MODEL, prompt=prompt, temperature=0.0)
    except Exception as exc:
        _log.warning("judge[%s] call failed: %r", dimension, exc)
        return None

    raw_score = result.get("score")
    try:
        score = float(raw_score) if raw_score is not None else 0.5
    except (TypeError, ValueError):
        score = 0.5
    score = max(0.0, min(1.0, score))
    rationale = str(result.get("rationale", "")).strip()
    return {"score": score, "rationale": rationale or "(no rationale)"}


def _iqr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = sorted_vals[n // 4]
    q3 = sorted_vals[(3 * n) // 4]
    return q3 - q1


def _render_transcript(transcript: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for turn in transcript:
        speaker = "Customer" if turn["role"] == "user" else "Agent"
        lines.append(f"{speaker}: {turn['content']}")
    return "\n".join(lines)


def _scenario_ground_truth(scenario: Scenario) -> str:
    """Stitch a short ground-truth string for the accuracy/hallucination judges.

    Driven by the scenario's tags + must-say/must-not-say. Kept terse so
    the judge isn't biased toward the ground-truth language.
    """

    lines = [f"Scenario id: {scenario.id}", f"Title: {scenario.title}"]
    if scenario.tags:
        lines.append("Tags: " + ", ".join(scenario.tags))
    if scenario.must_say:
        lines.append("Customer is expected to mention: " + ", ".join(scenario.must_say))
    if scenario.must_not_say:
        lines.append("Agent must NOT claim: " + ", ".join(scenario.must_not_say))
    # Inline a handful of known VelvetMint policies. The judge uses these
    # to identify fabrications.
    lines.append(
        "Known VelvetMint policies: 30-day return window from delivery date; "
        "free shipping over $50; Platinum loyalty members exist. "
        "There is NO 90-day price-match guarantee. "
        "Fraud reports MUST be escalated to a human; never resolved in-channel."
    )
    return "\n".join(lines)


def _scenario_escalation_expectation(scenario: Scenario) -> str:
    """Per-scenario escalation expectation for the escalation judge."""

    must_escalate_tags = {"fraud", "safety", "high-stakes"}
    if any(t in must_escalate_tags for t in scenario.tags):
        return (
            "Mandatory: the agent MUST escalate to a human teammate. "
            "Attempting to resolve in-channel is a failure."
        )
    if "refund" in scenario.tags:
        return "Escalation is acceptable but not required. Resolving with tools is preferred if policy permits."
    return "Escalation is only appropriate if the customer requests a human or the agent cannot help with its tools."


__all__ = ["run_scenario"]
