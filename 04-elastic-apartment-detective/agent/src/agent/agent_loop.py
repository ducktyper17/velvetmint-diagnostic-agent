"""ReAct-style investigation loop for the Elastic Apartment Detective.

The loop drives Gemini (via Vertex AI) through the Elastic Agent Builder tool
surface: it reads building memory, HPD violations, 311 signals, tenant
sentiment, and a neighborhood baseline, writes a normalized brief back to
Elastic, then finalizes a renter-risk report. A deterministic stub mirrors the
same tool sequence so the product runs end-to-end with no GCP credentials and
so the demo is bulletproof on stage.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import urlparse

from google import genai
from google.genai import types

from agent import prompts
from agent.config import Settings
from agent.tools import (
    BuildingMemory,
    ComplaintSignals,
    ElasticMCPClient,
    HPDViolations,
    NeighborhoodComparison,
    TenantSentiment,
    compare_to_neighborhood_baseline,
    get_311_signals,
    get_hpd_violations,
    normalize_address,
    save_building_brief,
    search_building_memory,
    search_tenant_sentiment,
)

log = logging.getLogger(__name__)

EventType = Literal["thought", "tool_call", "tool_result", "final_report", "error", "done"]

# Tool names the model may call to gather evidence (read side).
READ_TOOLS = frozenset(
    {
        "search_building_memory",
        "get_hpd_violations",
        "get_311_signals",
        "search_tenant_sentiment",
        "compare_to_neighborhood_baseline",
    }
)


@dataclass
class AgentEvent:
    """One event emitted to the SSE response."""

    type: EventType
    payload: dict[str, Any]
    iteration: int
    ts_ms: float = field(default_factory=lambda: time.time() * 1000)


@dataclass
class ListingContext:
    """Normalized listing input for one investigation."""

    address: str
    listing_url: str | None
    source: str
    user_question: str | None = None


@dataclass
class RiskReport:
    """Final renter-facing output."""

    address: str
    listing_source: str
    risk_score: float
    summary: str
    top_red_flags: list[str]
    questions_to_ask: list[str]
    evidence: list[str]


async def run_agent_loop(
    *,
    context: ListingContext,
    settings: Settings,
    mcp: ElasticMCPClient,
) -> AsyncIterator[AgentEvent]:
    """Drive the investigation with Gemini + Elastic and stream progress."""

    user_goal = (
        context.user_question.strip()
        if context.user_question
        else f"Investigate {context.address} and tell me what I should know before I sign."
    )
    history: list[dict[str, str]] = [
        {"role": "user", "content": user_goal},
    ]

    for iteration in range(1, settings.agent_max_iterations + 1):
        try:
            turn = await _call_gemini(history=history, settings=settings, context=context)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, never crashes the stream
            log.exception("agent_loop.gemini_error")
            yield AgentEvent("error", {"error": str(exc)}, iteration)
            return

        actionable = [c for c in turn.tool_calls if c.name != "finalize_brief"]

        if not actionable and turn.is_final:
            if not turn.final_payload:
                yield AgentEvent(
                    "error",
                    {"error": "Gemini finalized without a structured renter brief."},
                    iteration,
                )
                return
            report = turn.final_payload
            yield AgentEvent("thought", {"text": turn.final_thought}, iteration)
            yield AgentEvent(
                "final_report",
                {
                    "listing": {
                        "address": report.address,
                        "source": report.listing_source,
                        "listing_url": context.listing_url,
                    },
                    "risk_score": report.risk_score,
                    "summary": report.summary,
                    "top_red_flags": report.top_red_flags,
                    "questions_to_ask": report.questions_to_ask,
                    "evidence": report.evidence,
                },
                iteration,
            )
            yield AgentEvent("done", {"reason": "finalize_brief"}, iteration)
            return

        if not actionable:
            yield AgentEvent(
                "error", {"error": "Gemini returned no actionable tool call."}, iteration
            )
            return

        # Announce the batch up front, then fan the independent read tools out
        # concurrently — that is the bulk of per-investigation latency.
        for call in actionable:
            yield AgentEvent("thought", {"text": call.thought}, iteration)
            yield AgentEvent("tool_call", {"name": call.name, "args": call.args}, iteration)

        results = await asyncio.gather(
            *(_dispatch_tool(call, mcp=mcp, context=context) for call in actionable)
        )

        for call, tool_result in zip(actionable, results, strict=True):
            yield AgentEvent("tool_result", {"name": call.name, "result": tool_result}, iteration)
            history.append(
                {
                    "role": "tool",
                    "content": json.dumps({"tool": call.name, "result": tool_result}),
                }
            )

    yield AgentEvent(
        "error",
        {"error": "max iterations exceeded; aborting without a final brief"},
        settings.agent_max_iterations,
    )


# Human-friendly pacing (seconds) for the on-stage replay path, keyed by event
# type. Picked so the investigation panel reads at a watchable speed on camera.
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
    context: ListingContext,
    settings: Settings,
) -> AsyncIterator[AgentEvent]:
    """Stream a deterministic, paced investigation for bulletproof live demos.

    Forces the offline stub paths (no Gemini, no live Elastic, no network) and
    adds human-readable delays between events, so the story is identical every
    run and cannot fail on stage even with no credentials or connectivity.
    """

    replay_settings = settings.model_copy(
        update={"stub_gemini_responses": True, "demo_mode": True}
    )
    mcp = ElasticMCPClient(replay_settings)
    try:
        async for event in run_agent_loop(
            context=context, settings=replay_settings, mcp=mcp
        ):
            await asyncio.sleep(_REPLAY_PACING.get(event.type, 0.3))
            yield event
    finally:
        await mcp.aclose()


async def _dispatch_tool(
    call: _ToolCall,
    *,
    mcp: ElasticMCPClient,
    context: ListingContext,
) -> dict[str, Any]:
    """Execute one tool call and return its result dict (never raises)."""

    address = str(call.args.get("address", context.address)) or context.address
    try:
        if call.name == "search_building_memory":
            return (await search_building_memory(mcp, address=address)).model_dump()
        if call.name == "get_hpd_violations":
            return (await get_hpd_violations(mcp, address=address)).model_dump()
        if call.name == "get_311_signals":
            return (await get_311_signals(mcp, address=address)).model_dump()
        if call.name == "search_tenant_sentiment":
            return (await search_tenant_sentiment(mcp, address=address)).model_dump()
        if call.name == "compare_to_neighborhood_baseline":
            return (await compare_to_neighborhood_baseline(mcp, address=address)).model_dump()
        if call.name == "save_building_brief":
            return (
                await save_building_brief(
                    mcp,
                    address=address,
                    risk_score=_coerce_float(call.args.get("risk_score"), default=0.0) or 0.0,
                    summary=str(call.args.get("summary", "")),
                )
            ).model_dump()
        return {"error": f"unknown tool {call.name!r}"}
    except Exception as exc:  # noqa: BLE001 - reported back to the model as a tool error
        log.exception("agent_loop.tool_error", extra={"tool": call.name})
        return {"error": str(exc)}


def build_listing_context(
    *,
    address: str | None,
    listing_url: str | None,
    question: str | None,
    settings: Settings,
) -> ListingContext:
    """Normalize the incoming listing input into a single context object."""

    source = "manual"
    derived_address = address
    if listing_url:
        host = urlparse(listing_url).netloc.lower()
        if "streeteasy" in host:
            source = "StreetEasy"
        elif "zillow" in host:
            source = "Zillow"
        else:
            source = host or "listing_url"

        if not derived_address:
            derived_address = _extract_address_from_url(listing_url)

    if not derived_address:
        if settings.is_demo:
            derived_address = settings.demo_address
        else:
            raise ValueError("address extraction is not reliable enough yet; pass `address` too")

    # In demo mode, snap a slug-derived address back to the canonical demo
    # address so the renter brief shows a clean "123 Orchard St, New York, NY
    # 10002" instead of the title-cased URL slug.
    if settings.is_demo and _loose_match(derived_address, settings.demo_address):
        derived_address = settings.demo_address

    return ListingContext(
        address=normalize_address(derived_address),
        listing_url=listing_url,
        source=source,
        user_question=question,
    )


# --------------------------------------------------------------------------- #
# Gemini turn parsing
# --------------------------------------------------------------------------- #


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
    final_payload: RiskReport | None = None


async def _call_gemini(
    *,
    history: list[dict[str, str]],
    settings: Settings,
    context: ListingContext,
) -> _Turn:
    """Call Gemini via Vertex AI and parse the turn's tool decisions."""

    if settings.stub_gemini_responses:
        return _stub_turn(history=history, context=context)

    prompt = _render_model_prompt(history=history, context=context)
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
        raise RuntimeError("Gemini did not return a function call.")

    turn = _Turn()
    for function_call in function_calls:
        name = function_call.name or ""
        args = dict(function_call.args or {})
        thought = str(args.pop("thought", "")).strip() or _default_thought(name)

        if name == "finalize_brief":
            turn.is_final = True
            turn.final_thought = thought
            turn.final_payload = RiskReport(
                address=str(args.get("address", context.address)) or context.address,
                listing_source=context.source,
                risk_score=_coerce_float(args.get("risk_score"), default=0.0) or 0.0,
                summary=str(args.get("summary", "")),
                top_red_flags=_coerce_list(args.get("top_red_flags")) or ["limited public signals"],
                questions_to_ask=_coerce_list(args.get("questions_to_ask")),
                evidence=_coerce_list(args.get("evidence")),
            )
            continue

        turn.tool_calls.append(_ToolCall(name=name, args=args, thought=thought))

    return turn


@lru_cache(maxsize=4)
def _get_genai_client(*, project: str, location: str) -> genai.Client:
    """Return a cached Google Gen AI client for Vertex AI."""

    return genai.Client(vertexai=True, project=project, location=location)


def _function_declarations() -> list[types.FunctionDeclaration]:
    """Return the function declarations exposed to Gemini."""

    address_only = {
        "thought": {
            "type": "string",
            "description": "One short public reasoning line to stream to the UI.",
        },
        "address": {
            "type": "string",
            "description": "The normalized building address under investigation.",
        },
    }
    return [
        types.FunctionDeclaration(
            name="search_building_memory",
            description="Check Elastic for a prior brief on this address (memory index).",
            parameters_json_schema={
                "type": "object",
                "properties": address_only,
                "required": ["thought", "address"],
            },
        ),
        types.FunctionDeclaration(
            name="get_hpd_violations",
            description="ES|QL query over HPD violations: open count, severe categories, examples.",
            parameters_json_schema={
                "type": "object",
                "properties": address_only,
                "required": ["thought", "address"],
            },
        ),
        types.FunctionDeclaration(
            name="get_311_signals",
            description="ES|QL query over nearby NYC 311 complaints: volume, categories, noise mix.",
            parameters_json_schema={
                "type": "object",
                "properties": address_only,
                "required": ["thought", "address"],
            },
        ),
        types.FunctionDeclaration(
            name="search_tenant_sentiment",
            description="Hybrid (semantic + keyword) search over curated tenant-signal documents.",
            parameters_json_schema={
                "type": "object",
                "properties": address_only,
                "required": ["thought", "address"],
            },
        ),
        types.FunctionDeclaration(
            name="compare_to_neighborhood_baseline",
            description="Aggregate complaint density vs the ZIP baseline to flag outliers.",
            parameters_json_schema={
                "type": "object",
                "properties": address_only,
                "required": ["thought", "address"],
            },
        ),
        types.FunctionDeclaration(
            name="save_building_brief",
            description="Write the normalized brief back to the Elastic building_briefs index.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "One short public reasoning line to stream to the UI.",
                    },
                    "address": {"type": "string"},
                    "risk_score": {"type": "number"},
                    "summary": {"type": "string"},
                },
                "required": ["thought", "address", "risk_score", "summary"],
            },
        ),
        types.FunctionDeclaration(
            name="finalize_brief",
            description="Return the final renter-risk brief after the evidence is gathered and saved.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "One short public reasoning line to stream to the UI.",
                    },
                    "address": {"type": "string"},
                    "risk_score": {
                        "type": "number",
                        "description": "Overall renter risk from 0.0 (safe) to 10.0 (avoid).",
                    },
                    "summary": {"type": "string"},
                    "top_red_flags": {"type": "array", "items": {"type": "string"}},
                    "questions_to_ask": {"type": "array", "items": {"type": "string"}},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "thought",
                    "address",
                    "risk_score",
                    "summary",
                    "top_red_flags",
                    "questions_to_ask",
                ],
            },
        ),
    ]


def _render_model_prompt(*, history: list[dict[str, str]], context: ListingContext) -> str:
    """Flatten the conversation and tool history into a single prompt."""

    rendered_history = "\n".join(
        f"{item['role'].upper()}: {item['content']}" for item in history
    )
    return (
        f"{prompts.SYSTEM_PROMPT}\n\n"
        f"{prompts.render_few_shots()}\n\n"
        "Listing under investigation:\n"
        f"- address: {context.address}\n"
        f"- source: {context.source}\n"
        f"- listing_url: {context.listing_url or 'none'}\n\n"
        "Conversation so far:\n"
        f"{rendered_history}\n\n"
        "Every tool call must include a short public `thought`. The five read tools are "
        "independent — request them together in one turn. Then save_building_brief, then "
        "finalize_brief. Do not answer in plain text."
    )


def _default_thought(tool_name: str) -> str:
    """Return a fallback public thought when Gemini omits one."""

    defaults = {
        "search_building_memory": "Checking whether we already have a brief on this building.",
        "get_hpd_violations": "Pulling building-level housing violations.",
        "get_311_signals": "Checking nearby quality-of-life complaints.",
        "search_tenant_sentiment": "Searching tenant chatter for softer warning signs.",
        "compare_to_neighborhood_baseline": "Comparing this building to its neighborhood.",
        "save_building_brief": "Saving the normalized brief for fast follow-ups.",
        "finalize_brief": "I have enough evidence to write the renter brief.",
    }
    return defaults.get(tool_name, f"Calling {tool_name}.")


# --------------------------------------------------------------------------- #
# Deterministic stub (offline + replay)
# --------------------------------------------------------------------------- #


# Order the five read tools are issued in for a fresh investigation.
READ_TOOL_ORDER = [
    "search_building_memory",
    "get_hpd_violations",
    "get_311_signals",
    "search_tenant_sentiment",
    "compare_to_neighborhood_baseline",
]


def _stub_turn(*, history: list[dict[str, str]], context: ListingContext) -> _Turn:
    """Return a deterministic tool sequence for tests, offline work, and replay.

    A fresh investigation issues the five read tools in a single turn (mirroring
    the concurrent fast path the real model takes), then saves the brief, then
    finalizes — all grounded in the gathered results. A follow-up question takes
    the memory-reuse fast path instead: read the saved brief, pull one fresh
    signal, and answer — no full re-investigation.
    """

    done_tools = _completed_tools(history)
    address = context.address

    if context.user_question:
        followup = _followup_stub(history=history, context=context, done=done_tools)
        if followup is not None:
            return followup

    missing = [t for t in READ_TOOL_ORDER if t not in done_tools]
    if missing:
        calls: list[_ToolCall] = []
        for i, name in enumerate(missing):
            thought = (
                "Plan: pull memory, HPD, 311, sentiment, and baseline together."
                if i == 0 and len(missing) == len(READ_TOOL_ORDER)
                else _default_thought(name)
            )
            calls.append(_ToolCall(name=name, args={"address": address}, thought=thought))
        return _Turn(tool_calls=calls)

    report = _report_from_history(context=context, history=history)

    if "save_building_brief" not in done_tools:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="save_building_brief",
                    args={
                        "address": address,
                        "risk_score": report.risk_score,
                        "summary": report.summary,
                    },
                    thought="Saving the normalized brief so follow-ups skip the full investigation.",
                )
            ]
        )

    return _Turn(
        is_final=True,
        final_thought="I have enough evidence to write the renter brief.",
        final_payload=report,
    )


def _followup_stub(
    *, history: list[dict[str, str]], context: ListingContext, done: set[str]
) -> _Turn | None:
    """Memory-reuse fast path for a follow-up question.

    Returns ``None`` to fall back to a full investigation when there is no saved
    brief for this building yet (so a first-ever follow-up still works).
    """

    if "search_building_memory" not in done:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="search_building_memory",
                    args={"address": context.address},
                    thought="Follow-up — reading our saved Elastic brief for this building first.",
                )
            ]
        )

    memory = _latest_result(history, "search_building_memory") or {}
    if not memory.get("found"):
        return None  # no prior brief; fall through to a full investigation

    if "get_311_signals" not in done:
        return _Turn(
            tool_calls=[
                _ToolCall(
                    name="get_311_signals",
                    args={"address": context.address},
                    thought="Found a saved brief. Pulling the latest 311 signal to answer the question.",
                )
            ]
        )

    return _Turn(
        is_final=True,
        final_thought="Answering from the saved brief plus the latest signal — no need to re-investigate.",
        final_payload=_followup_report(context=context, history=history),
    )


def _followup_report(*, context: ListingContext, history: list[dict[str, str]]) -> RiskReport:
    """Build a focused brief that reuses the saved memory and answers the question."""

    memory = BuildingMemory.model_validate(
        {"address": context.address, "found": False, **(_latest_result(history, "search_building_memory") or {})}
    )
    complaints = ComplaintSignals.model_validate(
        {
            "address": context.address,
            "complaint_count_90d": 0,
            "nighttime_noise_share": 0.0,
            **(_latest_result(history, "get_311_signals") or {}),
        }
    )

    question = (context.user_question or "").strip()
    risk = memory.prior_risk_score if memory.prior_risk_score is not None else 5.0
    flags = _dedupe(list(memory.prior_flags))[:3] or ["limited public signals"]
    night_pct = round(complaints.nighttime_noise_share * 100)

    summary = f"Reusing the saved brief for {context.address} (risk {round(float(risk), 1)}/10)."
    if memory.summary:
        summary += f" {memory.summary}"
    if question:
        summary += f" On your question — “{question}” — the strongest signal is {flags[0]}."

    evidence: list[str] = []
    if memory.summary:
        evidence.append(memory.summary)
    evidence.append(
        f"{complaints.complaint_count_90d} complaints in the last 90 days; "
        f"{night_pct}% of nearby noise is late-night."
    )

    return RiskReport(
        address=context.address,
        listing_source=context.source,
        risk_score=round(float(risk), 1),
        summary=summary,
        top_red_flags=flags,
        questions_to_ask=[
            "How were the most recent building complaints resolved, and when?",
            "What is the plan for noise mitigation and quiet-hours enforcement?",
            "Are quiet hours actually enforced on weekends?",
        ],
        evidence=_dedupe(evidence)[:6],
    )


def _completed_tools(history: list[dict[str, str]]) -> set[str]:
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


def _latest_result(history: list[dict[str, str]], tool: str) -> dict[str, Any] | None:
    """Return the most recent result payload for a given tool from history."""

    for item in reversed(history):
        if item["role"] != "tool":
            continue
        try:
            parsed = json.loads(item["content"])
        except json.JSONDecodeError:
            continue
        if parsed.get("tool") == tool:
            result = parsed.get("result")
            return result if isinstance(result, dict) else None
    return None


def _report_from_history(*, context: ListingContext, history: list[dict[str, str]]) -> RiskReport:
    """Rebuild a grounded renter brief from the tool results already in history."""

    memory = _latest_result(history, "search_building_memory") or {}
    hpd = _latest_result(history, "get_hpd_violations") or {}
    complaints = _latest_result(history, "get_311_signals") or {}
    sentiment = _latest_result(history, "search_tenant_sentiment") or {}
    baseline = _latest_result(history, "compare_to_neighborhood_baseline") or {}

    return _build_report(
        context=context,
        memory=BuildingMemory.model_validate({"address": context.address, "found": False, **memory}),
        hpd=HPDViolations.model_validate({"address": context.address, "open_violations": 0, **hpd}),
        complaints=ComplaintSignals.model_validate(
            {"address": context.address, "complaint_count_90d": 0, "nighttime_noise_share": 0.0, **complaints}
        ),
        sentiment=TenantSentiment.model_validate(
            {"address": context.address, "mentions_found": 0, **sentiment}
        ),
        baseline=NeighborhoodComparison.model_validate(
            {"address": context.address, "complaint_index_vs_zip": 1.0, "summary": "", **baseline}
        ),
    )


def _build_report(
    *,
    context: ListingContext,
    memory: BuildingMemory,
    hpd: HPDViolations,
    complaints: ComplaintSignals,
    sentiment: TenantSentiment,
    baseline: NeighborhoodComparison,
) -> RiskReport:
    """Synthesize a renter-facing report from tool outputs."""

    score = 2.5
    flags: list[str] = []
    evidence: list[str] = []

    if memory.found and memory.prior_risk_score is not None:
        score += min(memory.prior_risk_score * 0.2, 1.5)
        flags.extend(memory.prior_flags)
        if memory.summary:
            evidence.append(memory.summary)

    if hpd.open_violations > 0:
        score += min(hpd.open_violations * 0.35, 2.0)
        flags.append(f"{hpd.open_violations} open HPD violations")
        evidence.extend(hpd.recent_examples)

    if complaints.complaint_count_90d >= 10:
        score += 1.5
        flags.append("elevated 311 complaint volume")
    if complaints.nighttime_noise_share >= 0.5:
        score += 1.0
        flags.append("high late-night noise share")
    if complaints.top_categories:
        evidence.append(f"Top 311 categories: {', '.join(complaints.top_categories[:3])}.")

    if sentiment.mentions_found > 0:
        score += min(sentiment.mentions_found * 0.4, 1.2)
        flags.append("tenant-sentiment concerns found")
        evidence.extend(sentiment.highlights)

    if baseline.complaint_index_vs_zip > 1.3:
        score += 1.2
        flags.append("complaint density above neighborhood baseline")
        if baseline.summary:
            evidence.append(baseline.summary)

    risk_score = round(min(score, 9.8), 1)
    unique_flags = _dedupe(flags)
    top_red_flags = unique_flags[:3] or ["limited public signals"]

    summary = (
        f"{context.address} scores {risk_score}/10 for renter risk. "
        f"The biggest concerns are {', '.join(top_red_flags[:2])}."
    )
    if context.user_question:
        summary += f" User focus: {context.user_question.strip()}"

    questions_to_ask = [
        "How were the most recent building complaints resolved, and when?",
        "What is the plan for noise mitigation and quiet-hours enforcement?",
        "Can management explain any open or recurring maintenance issues before move-in?",
    ]

    return RiskReport(
        address=context.address,
        listing_source=context.source,
        risk_score=risk_score,
        summary=summary,
        top_red_flags=top_red_flags,
        questions_to_ask=questions_to_ask,
        evidence=_dedupe(evidence)[:6],
    )


def _extract_address_from_url(listing_url: str) -> str | None:
    """Best-effort address extraction from a listing slug."""

    path = urlparse(listing_url).path.strip("/")
    if not path:
        return None
    slug = path.split("/")[-1]
    candidate = slug.replace("-", " ").replace("_", " ").strip()
    if not any(char.isdigit() for char in candidate):
        return None
    return candidate.title()


def _loose_match(a: str, b: str) -> bool:
    """Compare two addresses ignoring case, punctuation, and whitespace."""

    def canon(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    return canon(a) == canon(b)


def _coerce_float(value: Any, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output
