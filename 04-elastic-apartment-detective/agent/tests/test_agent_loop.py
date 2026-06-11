"""Tests for the offline (stub) investigation loop."""

from __future__ import annotations

import pytest

from agent.agent_loop import build_listing_context, run_agent_loop
from agent.config import Settings
from agent.tools import ElasticMCPClient


def _settings(**overrides: object) -> Settings:
    base = {
        "google_cloud_project": "test-project",
        "elastic_mcp_url": "http://localhost:3000/api/agent_builder/mcp",
        "elastic_mcp_api_key": "test-key",
        "demo_mode": True,
        "stub_gemini_responses": True,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


async def _collect(listing_url: str, settings: Settings) -> list:
    context = build_listing_context(
        address=None, listing_url=listing_url, question=None, settings=settings
    )
    mcp = ElasticMCPClient(settings)
    try:
        return [event async for event in run_agent_loop(context=context, settings=settings, mcp=mcp)]
    finally:
        await mcp.aclose()


@pytest.mark.asyncio
async def test_high_risk_demo_listing_finalizes_with_evidence() -> None:
    settings = _settings()
    events = await _collect(
        "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002", settings
    )

    types = [e.type for e in events]
    assert "final_report" in types
    assert types[-1] == "done"

    final = next(e for e in events if e.type == "final_report")
    assert final.payload["risk_score"] >= 7.0  # the seeded high-risk building
    assert final.payload["top_red_flags"]
    assert final.payload["evidence"]
    assert len(final.payload["questions_to_ask"]) == 3
    # Address is snapped back to the clean canonical form for the demo building.
    assert final.payload["listing"]["address"] == "123 Orchard St, New York, NY 10002"


@pytest.mark.asyncio
async def test_confidence_is_derived_from_corroborating_sources() -> None:
    settings = _settings()

    # Seeded high-risk building: 5 independent sources corroborate -> high.
    strong = await _collect(
        "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002", settings
    )
    strong_final = next(e for e in strong if e.type == "final_report")
    assert strong_final.payload["confidence"] == "high"
    assert "corroborate" in strong_final.payload["confidence_rationale"]

    # Thin building: only weak signals, no strong corroboration -> low + honest note.
    thin = await _collect("https://zillow.example/homes/55-mott-st", settings)
    thin_final = next(e for e in thin if e.type == "final_report")
    assert thin_final.payload["confidence"] == "low"
    assert "thin" in thin_final.payload["confidence_rationale"].lower()


@pytest.mark.asyncio
async def test_reads_fire_in_a_single_parallel_turn() -> None:
    settings = _settings()
    events = await _collect(
        "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002", settings
    )

    read_tools = {
        "search_building_memory",
        "get_hpd_violations",
        "get_311_signals",
        "search_tenant_sentiment",
        "compare_to_neighborhood_baseline",
    }
    first_iter_calls = {
        e.payload["name"]
        for e in events
        if e.type == "tool_call" and e.iteration == 1
    }
    assert read_tools <= first_iter_calls  # all five reads happen in iteration 1


@pytest.mark.asyncio
async def test_brief_is_saved_before_finalize() -> None:
    settings = _settings()
    events = await _collect("https://zillow.example/homes/55-mott-st", settings)

    tool_calls = [e.payload["name"] for e in events if e.type == "tool_call"]
    assert "save_building_brief" in tool_calls
    save_idx = tool_calls.index("save_building_brief")
    # Every read tool precedes the writeback.
    assert tool_calls.index("get_hpd_violations") < save_idx


async def _collect_with_question(listing_url: str, question: str, settings: Settings) -> list:
    context = build_listing_context(
        address=None, listing_url=listing_url, question=question, settings=settings
    )
    mcp = ElasticMCPClient(settings)
    try:
        return [event async for event in run_agent_loop(context=context, settings=settings, mcp=mcp)]
    finally:
        await mcp.aclose()


@pytest.mark.asyncio
async def test_followup_reuses_saved_brief_without_full_investigation() -> None:
    settings = _settings()
    events = await _collect_with_question(
        "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002",
        "What's the biggest concern if I work nights?",
        settings,
    )

    tool_calls = [e.payload["name"] for e in events if e.type == "tool_call"]
    # Memory-reuse fast path: reads the brief + one fresh signal, nothing else.
    assert tool_calls == ["search_building_memory", "get_311_signals"]
    assert "search_tenant_sentiment" not in tool_calls
    assert "save_building_brief" not in tool_calls

    final = next(e for e in events if e.type == "final_report")
    assert "saved brief" in final.payload["summary"].lower()
    assert final.payload["risk_score"] > 0


@pytest.mark.asyncio
async def test_followup_on_unseen_building_falls_back_to_full_investigation() -> None:
    # 55 Mott has no prior brief in demo data, so a follow-up must investigate.
    settings = _settings()
    events = await _collect_with_question(
        "https://zillow.example/homes/55-mott-st", "Is it quiet at night?", settings
    )
    tool_calls = [e.payload["name"] for e in events if e.type == "tool_call"]
    assert "compare_to_neighborhood_baseline" in tool_calls  # full investigation ran
    assert "final_report" in [e.type for e in events]


@pytest.mark.asyncio
async def test_unknown_address_in_non_demo_requires_address() -> None:
    settings = _settings(demo_mode=False)
    with pytest.raises(ValueError):
        build_listing_context(
            address=None,
            listing_url="https://streeteasy.example/listing/no-digits-here",
            question=None,
            settings=settings,
        )
