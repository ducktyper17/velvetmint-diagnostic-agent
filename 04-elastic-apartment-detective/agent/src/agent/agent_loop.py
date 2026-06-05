"""Streaming investigation loop for the Elastic Apartment Detective."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

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

EventType = Literal["thought", "tool_call", "tool_result", "final_report", "error", "done"]


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
    """Run a deterministic investigation loop until the live Gemini path lands."""

    iteration = 1
    address = normalize_address(context.address)

    yield AgentEvent(
        "thought",
        {"text": "Plan: check prior memory, hard evidence, neighborhood signals, and sentiment."},
        iteration,
    )

    memory = await _run_tool(
        iteration=iteration,
        name="search_building_memory",
        args={"address": address},
        caller=lambda: search_building_memory(mcp, address=address),
    )
    yield memory[0]
    yield memory[1]
    memory_result = BuildingMemory.model_validate(memory[1].payload["result"])
    iteration += 1

    yield AgentEvent(
        "thought",
        {"text": "Looking for building-level housing issues."},
        iteration,
    )
    hpd = await _run_tool(
        iteration=iteration,
        name="get_hpd_violations",
        args={"address": address},
        caller=lambda: get_hpd_violations(mcp, address=address),
    )
    yield hpd[0]
    yield hpd[1]
    hpd_result = HPDViolations.model_validate(hpd[1].payload["result"])
    iteration += 1

    yield AgentEvent(
        "thought",
        {"text": "Checking quality-of-life signals around the address."},
        iteration,
    )
    complaints = await _run_tool(
        iteration=iteration,
        name="get_311_signals",
        args={"address": address},
        caller=lambda: get_311_signals(mcp, address=address),
    )
    yield complaints[0]
    yield complaints[1]
    complaint_result = ComplaintSignals.model_validate(complaints[1].payload["result"])
    iteration += 1

    yield AgentEvent(
        "thought",
        {"text": "Searching for softer tenant-sentiment evidence."},
        iteration,
    )
    sentiment = await _run_tool(
        iteration=iteration,
        name="search_tenant_sentiment",
        args={"address": address},
        caller=lambda: search_tenant_sentiment(mcp, address=address),
    )
    yield sentiment[0]
    yield sentiment[1]
    sentiment_result = TenantSentiment.model_validate(sentiment[1].payload["result"])
    iteration += 1

    yield AgentEvent(
        "thought",
        {"text": "Comparing this building to the neighborhood baseline."},
        iteration,
    )
    baseline = await _run_tool(
        iteration=iteration,
        name="compare_to_neighborhood_baseline",
        args={"address": address},
        caller=lambda: compare_to_neighborhood_baseline(mcp, address=address),
    )
    yield baseline[0]
    yield baseline[1]
    baseline_result = NeighborhoodComparison.model_validate(baseline[1].payload["result"])
    iteration += 1

    report = _build_report(
        context=context,
        memory=memory_result,
        hpd=hpd_result,
        complaints=complaint_result,
        sentiment=sentiment_result,
        baseline=baseline_result,
    )

    summary = report.summary
    saved = await _run_tool(
        iteration=iteration,
        name="save_building_brief",
        args={"address": address, "risk_score": report.risk_score, "summary": summary},
        caller=lambda: save_building_brief(
            mcp,
            address=address,
            risk_score=report.risk_score,
            summary=summary,
        ),
    )
    yield saved[0]
    yield saved[1]

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
    yield AgentEvent("done", {"reason": "finalize_investigation"}, iteration)
    _ = settings


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

    return ListingContext(
        address=normalize_address(derived_address),
        listing_url=listing_url,
        source=source,
        user_question=question,
    )


async def _run_tool(
    *,
    iteration: int,
    name: str,
    args: dict[str, Any],
    caller: Any,
) -> tuple[AgentEvent, AgentEvent]:
    """Wrap one tool call in tool_call and tool_result events."""

    call_event = AgentEvent("tool_call", {"name": name, "args": args}, iteration)
    result = await caller()
    result_event = AgentEvent(
        "tool_result",
        {"name": name, "result": result.model_dump()},
        iteration,
    )
    return call_event, result_event


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
