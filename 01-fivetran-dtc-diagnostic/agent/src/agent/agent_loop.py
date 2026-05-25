"""ReAct-style agent loop: Gemini 3 plans, picks tools, dispatches them.

The loop is intentionally simple and easy to reason about for hackathon
judges who skim the source:

    1. Build a single multi-turn prompt: system + few-shots + history.
    2. Call Gemini 3 (Vertex AI). Parse a tool call out of the response.
    3. Dispatch the tool via :mod:`agent.tools`.
    4. Append the tool result as a new turn.
    5. Repeat until Gemini calls ``finalize_diagnosis`` or we hit the
       iteration cap.

Each step yields an :class:`AgentEvent` so the FastAPI handler can stream
the loop's progress to the browser via SSE.

The actual Vertex AI invocation is stubbed with a TODO — we'll fill it in
on Day 2 of the build plan once we've confirmed the Gemini 3 model slug
and the function-calling JSON schema in Vertex's API.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from agent import prompts
from agent.config import Settings
from agent.diagnostic_engine import Finding, run_battery
from agent.tools import (
    FivetranMCPClient,
    check_sync_status,
    query_synced_data,
    setup_connector,
    trigger_sync,
)


log = logging.getLogger(__name__)


EventType = Literal[
    "thought", "tool_call", "tool_result", "final_report", "error", "done"
]


@dataclass
class AgentEvent:
    """One event emitted during a /diagnose call.

    The FastAPI handler serializes these as SSE messages with
    ``event: {type}`` and JSON payload.
    """

    type: EventType
    payload: dict[str, Any]
    iteration: int
    ts_ms: float = field(default_factory=lambda: time.time() * 1000)


@dataclass
class AgentRequest:
    """Input to :func:`run_agent_loop`."""

    question: str
    brand_id: str
    conversation_id: str


async def run_agent_loop(
    *,
    request: AgentRequest,
    settings: Settings,
    mcp: FivetranMCPClient,
) -> AsyncIterator[AgentEvent]:
    """Drive the ReAct loop. Yields :class:`AgentEvent` until done.

    The function is an async generator so the caller (FastAPI handler) can
    forward each event straight to the SSE response without buffering.
    """
    history: list[dict[str, str]] = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "system", "content": prompts.render_few_shots()},
        {"role": "user", "content": request.question},
    ]

    # State that the loop needs to remember across iterations. Kept tiny on
    # purpose; anything more elaborate belongs in MongoDB.
    fivetran_destination_id = _resolve_destination_id(settings, request.brand_id)
    fivetran_group_id = _resolve_group_id(settings, request.brand_id)

    for iteration in range(1, settings.agent_max_iterations + 1):
        try:
            decision = await _call_gemini(history=history, settings=settings)
        except Exception as exc:
            log.exception("agent_loop.gemini_error")
            yield AgentEvent("error", {"error": str(exc)}, iteration)
            return

        yield AgentEvent("thought", {"text": decision.thought}, iteration)

        if decision.is_final:
            findings = decision.final_findings or await run_battery(brand_id=request.brand_id)
            yield AgentEvent(
                "final_report",
                {"findings": [_finding_to_dict(f) for f in findings]},
                iteration,
            )
            yield AgentEvent("done", {"reason": "finalize_diagnosis"}, iteration)
            return

        tool = decision.tool_name
        args = decision.tool_args
        yield AgentEvent("tool_call", {"name": tool, "args": args}, iteration)

        # Dispatch table. Keep this in sync with prompts.SYSTEM_PROMPT.
        try:
            if tool == "setup_connector":
                result = await setup_connector(
                    mcp,
                    source=args["source"],
                    destination_id=fivetran_destination_id,
                    group_id=fivetran_group_id,
                )
                tool_result = result.model_dump()
            elif tool == "trigger_sync":
                tool_result = (await trigger_sync(mcp, args["connection_id"])).model_dump()
            elif tool == "check_sync_status":
                tool_result = (
                    await check_sync_status(mcp, args["connection_id"])
                ).model_dump()
            elif tool == "query_synced_data":
                tool_result = (
                    await query_synced_data(
                        metric=args["metric"],
                        window_days=int(args.get("window_days", 30)),
                        brand_id=request.brand_id,
                    )
                ).model_dump()
            else:
                tool_result = {"error": f"unknown tool {tool!r}"}
        except Exception as exc:
            log.exception("agent_loop.tool_error", extra={"tool": tool})
            tool_result = {"error": str(exc)}

        yield AgentEvent("tool_result", {"name": tool, "result": tool_result}, iteration)
        history.append(
            {
                "role": "tool",
                "content": json.dumps({"tool": tool, "result": tool_result}),
            }
        )

    yield AgentEvent(
        "error",
        {"error": "max iterations exceeded; aborting without final report"},
        settings.agent_max_iterations,
    )


# ---------------------------------------------------------------------------
# Gemini 3 invocation
# ---------------------------------------------------------------------------


@dataclass
class _ModelDecision:
    """One Gemini-3 response, parsed.

    Either a tool call (``tool_name`` set) or a final answer (``is_final``).
    """

    thought: str
    is_final: bool = False
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    final_findings: list[Finding] | None = None


async def _call_gemini(*, history: list[dict[str, str]], settings: Settings) -> _ModelDecision:
    """Call Gemini 3 with function-calling enabled and parse the response.

    TODO: replace with the real Vertex AI call. The skeleton:

        from vertexai.generative_models import GenerativeModel, Tool
        model = GenerativeModel(
            settings.vertex_model,
            tools=[_TOOL_SCHEMA],
            system_instruction=prompts.SYSTEM_PROMPT,
        )
        resp = await model.generate_content_async(history)
        return _parse_decision(resp)

    Until then we return a deterministic stub so the loop is testable.
    """
    _ = history, settings
    # Stub: the agent immediately asks for setup_connector(shopify) on turn 1
    # and finalizes on turn 2 to keep tests fast.
    if len(history) <= 3:
        return _ModelDecision(
            thought="Plan: pull data from every channel that influences revenue.",
            tool_name="setup_connector",
            tool_args={"source": "shopify"},
        )
    return _ModelDecision(
        thought="I have enough evidence; finalizing.",
        is_final=True,
        final_findings=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding_to_dict(f: Finding) -> dict[str, Any]:
    """Serialize a :class:`Finding` for SSE / Mongo storage."""
    return {
        "title": f.title,
        "category": f.category,
        "metric": f.metric,
        "current_value": f.current_value,
        "baseline_value": f.baseline_value,
        "delta_pct": f.delta_pct,
        "revenue_impact_usd": f.revenue_impact_usd,
        "confidence": f.confidence,
        "root_cause": f.root_cause,
        "recommended_fix": f.recommended_fix,
        "evidence": f.evidence,
    }


def _resolve_destination_id(settings: Settings, brand_id: str) -> str:
    """Look up the Fivetran destination id for ``brand_id``.

    For the demo we use a single destination per brand. In multi-tenant
    production we'd pull this from MongoDB. For now: env-var fallback.
    """
    # TODO: replace with MongoDB lookup keyed on brand_id once we have
    # multi-brand support. Day-12 work.
    _ = settings, brand_id
    return "REPLACE_ME_FIVETRAN_DESTINATION_ID"


def _resolve_group_id(settings: Settings, brand_id: str) -> str:
    """Look up the Fivetran group id for ``brand_id``."""
    # TODO: same as above.
    _ = settings, brand_id
    return "REPLACE_ME_FIVETRAN_GROUP_ID"
