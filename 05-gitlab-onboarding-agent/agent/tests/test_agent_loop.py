from __future__ import annotations

from agent.agent_loop import IncidentRequest, run_incident_loop
from agent.config import Settings
from agent.tools import GitLabMCPClient


async def test_incident_loop_emits_final_report_with_deployment() -> None:
    settings = Settings(
        demo_mode=True,
        use_gemini_summary=False,
        gitlab_mcp_token="token",
    )
    gitlab = GitLabMCPClient(settings)
    request = IncidentRequest(
        incident_title="Critical log4js vulnerability",
        cve_id="CVE-2026-4242",
        vulnerable_package="log4js",
        fixed_version="6.9.1",
    )

    events = [event async for event in run_incident_loop(request=request, settings=settings, gitlab=gitlab)]

    await gitlab.aclose()

    final_report = next(event for event in events if event.type == "final_report")

    assert final_report.payload["services_affected"] == 3
    assert final_report.payload["highest_risk_service"] == "checkout-service"
    assert len(final_report.payload["merge_requests"]) == 3
    assert len(final_report.payload["deployments"]) == 1
    assert final_report.payload["deployments"][0]["service_name"] == "analytics-worker"
