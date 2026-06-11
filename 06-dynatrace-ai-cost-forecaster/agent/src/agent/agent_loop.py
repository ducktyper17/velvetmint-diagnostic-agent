"""ReAct-style investigation loop for Agent Reliability Guard."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from google import genai
from google.genai import types

from agent import prompts
from agent.config import Settings
from agent.tools import (
    DynatraceMCPClient,
    draft_notebook,
    forecast_blast_radius,
    notify_owner,
    query_runtime_signals,
    run_change_analysis,
)

log = logging.getLogger(__name__)


EventType = Literal[
    "thought", "tool_call", "tool_result", "final_report", "error", "done"
]


@dataclass
class AgentEvent:
    """One event emitted during an investigation."""

    type: EventType
    payload: dict[str, Any]
    iteration: int
    ts_ms: float = field(default_factory=lambda: time.time() * 1000)


@dataclass
class AgentRequest:
    """Input to the investigation loop."""

    question: str
    service_name: str
    release_id: str | None
    lookback_minutes: int
    conversation_id: str


@dataclass
class InvestigationSummary:
    """Structured final output sent to the client."""

    summary: str
    probable_root_cause: str
    impact: str
    recommended_fix: str


async def run_agent_loop(
    *,
    request: AgentRequest,
    settings: Settings,
    mcp: DynatraceMCPClient,
) -> AsyncIterator[AgentEvent]:
    """Drive the investigation loop and stream progress as events."""

    history: list[dict[str, str]] = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "system", "content": prompts.render_few_shots()},
        {"role": "user", "content": request.question},
    ]
    # Accumulated read-tool results, keyed by tool name, so a later draft_notebook
    # call can assemble a full evidence-backed notebook instead of a blurb.
    evidence: dict[str, Any] = {}

    for iteration in range(1, settings.agent_max_iterations + 1):
        try:
            turn = await _call_gemini(history=history, settings=settings, request=request)
        except Exception as exc:
            log.exception("agent_loop.gemini_error")
            yield AgentEvent("error", {"error": str(exc)}, iteration)
            return

        # Independent read tools can run in one turn; finalize is deferred until
        # the model has seen their results, so we ignore a same-turn finalize if
        # the model also asked for tool calls.
        actionable = [c for c in turn.tool_calls if c.name != "finalize_investigation"]

        if not actionable and turn.is_final:
            if not turn.final_payload:
                yield AgentEvent(
                    "error",
                    {"error": "Gemini finalized without a structured payload."},
                    iteration,
                )
                return
            yield AgentEvent("thought", {"text": turn.final_thought}, iteration)
            yield AgentEvent(
                "final_report",
                {
                    "summary": turn.final_payload.summary,
                    "probable_root_cause": turn.final_payload.probable_root_cause,
                    "impact": turn.final_payload.impact,
                    "recommended_fix": turn.final_payload.recommended_fix,
                },
                iteration,
            )
            yield AgentEvent("done", {"reason": "finalize_investigation"}, iteration)
            return

        if not actionable:
            yield AgentEvent(
                "error",
                {"error": "Gemini returned no actionable tool call."},
                iteration,
            )
            return

        # Announce every call in the batch up front (thought + tool_call), then
        # fan the tool work out concurrently — the read tools no longer block one
        # another, which is the bulk of the per-investigation latency.
        for call in actionable:
            yield AgentEvent("thought", {"text": call.thought}, iteration)
            yield AgentEvent("tool_call", {"name": call.name, "args": call.args}, iteration)

        results = await asyncio.gather(
            *(
                _dispatch_tool(
                    call, mcp=mcp, settings=settings, request=request, evidence=evidence
                )
                for call in actionable
            )
        )

        for call, tool_result in zip(actionable, results, strict=True):
            # Remember read-tool results so a later draft_notebook in this run can
            # build the full evidence notebook.
            if call.name in {
                "query_runtime_signals",
                "run_change_analysis",
                "forecast_blast_radius",
            }:
                evidence[call.name] = tool_result
            yield AgentEvent(
                "tool_result", {"name": call.name, "result": tool_result}, iteration
            )
            history.append(
                {
                    "role": "tool",
                    "content": json.dumps({"tool": call.name, "result": tool_result}),
                }
            )

    yield AgentEvent(
        "error",
        {"error": "max iterations exceeded; aborting without final report"},
        settings.agent_max_iterations,
    )


async def _dispatch_tool(
    call: _ToolCall,
    *,
    mcp: DynatraceMCPClient,
    settings: Settings,
    request: AgentRequest,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one tool call and return its result dict (never raises)."""

    args = call.args
    service_name = str(args.get("service_name", request.service_name))
    lookback_minutes = int(args.get("lookback_minutes", request.lookback_minutes))
    release_id = _optional_str(args.get("release_id", request.release_id))

    try:
        if call.name == "query_runtime_signals":
            return (
                await query_runtime_signals(
                    mcp,
                    service_name=service_name,
                    lookback_minutes=lookback_minutes,
                    release_id=release_id,
                )
            ).model_dump()
        if call.name == "run_change_analysis":
            return (
                await run_change_analysis(
                    mcp,
                    service_name=service_name,
                    lookback_minutes=lookback_minutes,
                    release_id=release_id,
                )
            ).model_dump()
        if call.name == "forecast_blast_radius":
            return (
                await forecast_blast_radius(
                    mcp,
                    service_name=service_name,
                    lookback_minutes=lookback_minutes,
                    release_id=release_id,
                )
            ).model_dump()
        if call.name == "draft_notebook":
            return (
                await draft_notebook(
                    mcp,
                    title=str(
                        args.get(
                            "title",
                            f"{settings.dynatrace_default_notebook_name} - {request.service_name}",
                        )
                    ),
                    summary=str(args.get("summary", "Investigation evidence notebook.")),
                    evidence=evidence,
                )
            ).model_dump()
        if call.name == "notify_owner":
            return (
                await notify_owner(
                    mcp,
                    channel=str(args.get("channel", settings.dynatrace_notification_channel)),
                    summary=str(args.get("summary", "Agent reliability regression detected.")),
                )
            ).model_dump()
        return {"error": f"unknown tool {call.name!r}"}
    except Exception as exc:
        log.exception("agent_loop.tool_error", extra={"tool": call.name})
        return {"error": str(exc)}


# Human-friendly pacing (seconds) for the on-stage replay path, keyed by event
# type. Picked so the thinking panel reads at a watchable speed on camera.
_REPLAY_PACING: dict[str, float] = {
    "thought": 0.55,
    "tool_call": 0.3,
    "tool_result": 0.85,
    "final_report": 0.7,
    "done": 0.2,
    "error": 0.3,
}


async def run_replay(
    *,
    request: AgentRequest,
    settings: Settings,
) -> AsyncIterator[AgentEvent]:
    """Stream a deterministic, paced investigation for bulletproof live demos.

    Forces the offline stub paths (no Gemini, no Dynatrace, no network) and adds
    human-readable delays between events, so the story is identical every run and
    cannot fail on stage even with no credentials or connectivity.
    """

    replay_settings = settings.model_copy(
        update={"stub_gemini_responses": True, "stub_dynatrace_tools": True}
    )
    mcp = DynatraceMCPClient(replay_settings)
    try:
        async for event in run_agent_loop(
            request=request, settings=replay_settings, mcp=mcp
        ):
            await asyncio.sleep(_REPLAY_PACING.get(event.type, 0.3))
            yield event
    finally:
        await mcp.aclose()


@dataclass
class _ToolCall:
    """One tool invocation the model asked for, with its public thought."""

    name: str
    args: dict[str, Any]
    thought: str


@dataclass
class _Turn:
    """One parsed Gemini turn — may carry several tool calls and/or a finalize."""

    tool_calls: list[_ToolCall] = field(default_factory=list)
    is_final: bool = False
    final_thought: str = ""
    final_payload: InvestigationSummary | None = None


async def _call_gemini(
    *,
    history: list[dict[str, str]],
    settings: Settings,
    request: AgentRequest,
) -> _Turn:
    """Call Gemini via Vertex AI and parse the turn's tool decisions."""

    if settings.stub_gemini_responses:
        return _stub_turn(history)

    prompt = _render_model_prompt(history=history, request=request)
    tool = types.Tool(function_declarations=_function_declarations())
    config = types.GenerateContentConfig(
        temperature=0,
        tools=[tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
    )

    client = _get_genai_client(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.vertex_model,
        contents=prompt,
        config=config,
    )

    function_calls = response.function_calls or []
    if not function_calls:
        text = (response.text or "").strip()
        if text:
            return _Turn(
                is_final=True,
                final_thought="Gemini returned plain text instead of a tool call.",
                final_payload=InvestigationSummary(
                    summary=text,
                    probable_root_cause="Gemini did not emit a structured final tool call.",
                    impact="Unknown",
                    recommended_fix="Retry with structured tool forcing enabled.",
                ),
            )
        raise RuntimeError("Gemini did not return a function call.")

    turn = _Turn()
    for function_call in function_calls:
        args = dict(function_call.args or {})
        thought = str(args.pop("thought", "")).strip() or _default_thought(function_call.name)

        if function_call.name == "finalize_investigation":
            turn.is_final = True
            turn.final_thought = thought
            turn.final_payload = InvestigationSummary(
                summary=str(args.get("summary", "")),
                probable_root_cause=str(args.get("probable_root_cause", "")),
                impact=str(args.get("impact", "")),
                recommended_fix=str(args.get("recommended_fix", "")),
            )
            continue

        turn.tool_calls.append(
            _ToolCall(name=function_call.name, args=args, thought=thought)
        )

    return turn


@lru_cache(maxsize=4)
def _get_genai_client(*, project: str, location: str) -> genai.Client:
    """Return a cached Google Gen AI client for Vertex AI."""

    return genai.Client(vertexai=True, project=project, location=location)


def _function_declarations() -> list[types.FunctionDeclaration]:
    """Return the function declarations exposed to Gemini."""

    shared_service_properties = {
        "thought": {
            "type": "string",
            "description": "One short public reasoning line to stream to the UI.",
        },
        "service_name": {
            "type": "string",
            "description": "The affected Gemini-powered service or application.",
        },
        "lookback_minutes": {
            "type": "integer",
            "description": "How far back to inspect telemetry.",
        },
        "release_id": {
            "type": "string",
            "description": "Optional release marker or deployment identifier.",
        },
    }
    return [
        types.FunctionDeclaration(
            name="query_runtime_signals",
            description="Query Dynatrace for latency, token, and tool-failure signals.",
            parameters_json_schema={
                "type": "object",
                "properties": shared_service_properties,
                "required": ["thought", "service_name", "lookback_minutes"],
            },
        ),
        types.FunctionDeclaration(
            name="run_change_analysis",
            description="Run change or anomaly analysis for the service.",
            parameters_json_schema={
                "type": "object",
                "properties": shared_service_properties,
                "required": ["thought", "service_name", "lookback_minutes"],
            },
        ),
        types.FunctionDeclaration(
            name="forecast_blast_radius",
            description="Forecast the cost or latency impact if the regression remains live.",
            parameters_json_schema={
                "type": "object",
                "properties": shared_service_properties,
                "required": ["thought", "service_name", "lookback_minutes"],
            },
        ),
        types.FunctionDeclaration(
            name="draft_notebook",
            description="Create a Dynatrace notebook that captures the investigation evidence.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "One short public reasoning line to stream to the UI.",
                    },
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["thought", "title", "summary"],
            },
        ),
        types.FunctionDeclaration(
            name="notify_owner",
            description="Send an operator-facing notification once the notebook is ready.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "One short public reasoning line to stream to the UI.",
                    },
                    "channel": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["thought", "channel", "summary"],
            },
        ),
        types.FunctionDeclaration(
            name="finalize_investigation",
            description="Return the final operator-ready answer after enough evidence exists.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "One short public reasoning line to stream to the UI.",
                    },
                    "summary": {"type": "string"},
                    "probable_root_cause": {"type": "string"},
                    "impact": {"type": "string"},
                    "recommended_fix": {"type": "string"},
                },
                "required": [
                    "thought",
                    "summary",
                    "probable_root_cause",
                    "impact",
                    "recommended_fix",
                ],
            },
        ),
    ]


def _render_model_prompt(*, history: list[dict[str, str]], request: AgentRequest) -> str:
    """Flatten the conversation and tool history into a single prompt."""

    rendered_history = "\n".join(
        f"{item['role'].upper()}: {item['content']}"
        for item in history
        if item["role"] != "system"
    )
    return (
        f"{prompts.SYSTEM_PROMPT}\n\n"
        f"{prompts.render_few_shots()}\n\n"
        "Case metadata:\n"
        f"- service_name: {request.service_name}\n"
        f"- release_id: {request.release_id or 'none'}\n"
        f"- lookback_minutes: {request.lookback_minutes}\n"
        f"- conversation_id: {request.conversation_id}\n\n"
        "Conversation so far:\n"
        f"{rendered_history}\n\n"
        "Choose exactly one tool call. Every tool call must include a short public `thought`.\n"
        "Do not answer in plain text. Use finalize_investigation when you have enough evidence."
    )


def _default_thought(tool_name: str) -> str:
    """Return a fallback public thought when Gemini omits one."""

    defaults = {
        "query_runtime_signals": "Inspecting the core runtime signals first.",
        "run_change_analysis": "Looking for the boundary where the regression began.",
        "forecast_blast_radius": "Estimating the cost of leaving this live.",
        "draft_notebook": "Packaging the evidence into a shareable notebook.",
        "notify_owner": "Alerting the operator with the evidence in hand.",
        "finalize_investigation": "I have enough evidence to finalize the investigation.",
    }
    return defaults.get(tool_name, f"Calling {tool_name}.")


def _optional_str(value: Any) -> str | None:
    """Return a string for truthy values, otherwise None."""

    if value in (None, "", "null"):
        return None
    return str(value)


def _stub_completed_tools(history: list[dict[str, str]]) -> set[str]:
    """Return the set of tool names that already produced a result in history."""

    completed: set[str] = set()
    for item in history:
        if item["role"] != "tool":
            continue
        try:
            tool_name = json.loads(item["content"]).get("tool")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(tool_name, str):
            completed.add(tool_name)
    return completed


def _stub_turn(history: list[dict[str, str]]) -> _Turn:
    """Return a deterministic tool sequence for tests and offline work.

    The three read tools are issued in a single turn so the stub mirrors the
    concurrent fast path the real model is now prompted to take.
    """

    done_tools = _stub_completed_tools(history)

    if not {"query_runtime_signals", "run_change_analysis", "forecast_blast_radius"} & done_tools:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="query_runtime_signals",
                    args={"service_name": "refund-assistant", "lookback_minutes": 180},
                    thought="Plan: pull runtime signals, changepoint, and forecast in parallel.",
                ),
                _ToolCall(
                    name="run_change_analysis",
                    args={"service_name": "refund-assistant", "lookback_minutes": 180},
                    thought="Locating the boundary where the regression began.",
                ),
                _ToolCall(
                    name="forecast_blast_radius",
                    args={"service_name": "refund-assistant", "lookback_minutes": 180},
                    thought="Estimating the cost of leaving this live.",
                ),
            ]
        )
    if "draft_notebook" not in done_tools:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="draft_notebook",
                    args={
                        "title": "agent-reliability-guard - refund-assistant",
                        "summary": "The service regressed immediately after the release marker.",
                    },
                    thought="Packaging the evidence into a notebook for the operator.",
                )
            ]
        )
    if "notify_owner" not in done_tools:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="notify_owner",
                    args={
                        "channel": "#ai-platform-alerts",
                        "summary": "refund-assistant regressed after release-2026-05-26-bad-prompt.",
                    },
                    thought="The notebook is ready. Sending an operational notification now.",
                )
            ]
        )
    return _Turn(
        is_final=True,
        final_thought="I have enough evidence to finalize the investigation.",
        final_payload=InvestigationSummary(
            summary=(
                "refund-assistant regressed immediately after the release: token burn, "
                "latency, and tool failures all moved in the wrong direction."
            ),
            probable_root_cause=(
                "The new prompt or tool behavior likely created a refund-check retry loop "
                "on ambiguous refund requests."
            ),
            impact=(
                "Current behavior is adding user wait time and is projected to waste "
                "roughly $3.4k in one week if left unchanged."
            ),
            recommended_fix=(
                "Roll back the latest prompt version or cap refund_check retries to a single pass."
            ),
        ),
    )
