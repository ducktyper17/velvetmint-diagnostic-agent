from __future__ import annotations

import pytest

from agent.agent_loop import AgentRequest, run_agent_loop, run_replay
from agent.config import Settings
from agent.tools import DynatraceMCPClient


@pytest.mark.asyncio
async def test_agent_loop_emits_final_report() -> None:
    settings = Settings(
        google_cloud_project="rapid-agent-hack-2026",
        dynatrace_environment_url="https://demo.apps.dynatrace.com",
        dynatrace_mcp_url="http://localhost:3333",
        dynatrace_mcp_token="test-token",
        stub_gemini_responses=True,
        stub_dynatrace_tools=True,
    )
    client = DynatraceMCPClient(settings)

    try:
        request = AgentRequest(
            question="Investigate the refund assistant regression.",
            service_name="refund-assistant",
            release_id="release-2026-05-26-bad-prompt",
            lookback_minutes=180,
            conversation_id="test-conversation",
        )
        events = [
            event
            async for event in run_agent_loop(
                request=request,
                settings=settings,
                mcp=client,
            )
        ]
    finally:
        await client.aclose()

    assert any(
        event.type == "tool_call" and event.payload["name"] == "query_runtime_signals"
        for event in events
    )
    assert any(event.type == "final_report" for event in events)
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_run_replay_emits_complete_investigation() -> None:
    settings = Settings(
        google_cloud_project="rapid-agent-hack-2026",
        dynatrace_environment_url="https://demo.apps.dynatrace.com",
        dynatrace_mcp_url="http://localhost:3333",
        dynatrace_mcp_token="test-token",
        demo_mode=True,
    )

    request = AgentRequest(
        question="Investigate the refund assistant regression.",
        service_name="refund-assistant",
        release_id="release-2026-05-26-bad-prompt",
        lookback_minutes=180,
        conversation_id="replay-conversation",
    )

    events = [event async for event in run_replay(request=request, settings=settings)]

    final_reports = [event for event in events if event.type == "final_report"]
    assert len(final_reports) == 1, "replay must produce exactly one final_report"

    payload = final_reports[0].payload
    assert payload["summary"], "final_report.summary must be non-empty"
    assert payload["probable_root_cause"], "final_report.probable_root_cause must be non-empty"
    assert payload["impact"], "final_report.impact must be non-empty"
    assert payload["recommended_fix"], "final_report.recommended_fix must be non-empty"

    assert events[-1].type == "done"
