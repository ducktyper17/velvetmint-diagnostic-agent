"""Incident-response loop for the Blast Radius agent."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from agent import prompts
from agent.config import Settings
from agent.grounding import render_grounding_context
from agent.scenario import VulnerabilityEvent, get_default_vulnerability, rank_affected_services
from agent.tools import GitLabMCPClient
from agent.vertex_ai import generate_text


log = logging.getLogger(__name__)


EventType = Literal[
    "thought",
    "tool_call",
    "tool_result",
    "final_report",
    "error",
    "done",
]


@dataclass
class AgentEvent:
    """One event in the streamed incident timeline."""

    type: EventType
    payload: dict[str, Any]
    iteration: int
    ts_ms: float = field(default_factory=lambda: time.time() * 1000)


@dataclass
class IncidentRequest:
    """Input to the incident loop."""

    incident_title: str
    cve_id: str
    vulnerable_package: str
    fixed_version: str

    def to_event(self) -> VulnerabilityEvent:
        return VulnerabilityEvent(
            incident_title=self.incident_title,
            cve_id=self.cve_id,
            vulnerable_package=self.vulnerable_package,
            fixed_version=self.fixed_version,
        )


async def run_incident_loop(
    *,
    request: IncidentRequest | None,
    settings: Settings,
    gitlab: GitLabMCPClient,
) -> AsyncIterator[AgentEvent]:
    """Run the incident workflow and stream tool-backed actions."""

    _ = prompts.SYSTEM_PROMPT, prompts.render_few_shots()
    event = request.to_event() if request is not None else get_default_vulnerability()
    affected = rank_affected_services(
        event,
        auto_deploy_max_risk=settings.auto_deploy_max_risk,
    )

    if not affected:
        yield AgentEvent(
            "error",
            {"error": f"no affected services found for {event.vulnerable_package}"},
            0,
        )
        return

    grounding = render_grounding_context()
    iteration = 1
    yield AgentEvent(
        "thought",
        {
            "text": (
                f"Loaded service catalog and runbooks. Scanning for {event.vulnerable_package}."
            ),
            "cve_id": event.cve_id,
        },
        iteration,
    )

    yield AgentEvent("tool_call", {"name": "list_group_projects", "args": {}}, iteration)
    projects = await gitlab.list_group_projects()
    yield AgentEvent(
        "tool_result",
        {"name": projects.name, "result": projects.model_dump()},
        iteration,
    )

    iteration += 1
    yield AgentEvent(
        "thought",
        {"text": "Inspecting dependency manifests and ranking blast radius."},
        iteration,
    )
    yield AgentEvent(
        "tool_call",
        {"name": "inspect_dependency_files", "args": {"package": event.vulnerable_package}},
        iteration,
    )
    dependencies = await gitlab.inspect_dependency_files(event)
    yield AgentEvent(
        "tool_result",
        {"name": dependencies.name, "result": dependencies.model_dump()},
        iteration,
    )

    iteration += 1
    yield AgentEvent(
        "thought",
        {
            "text": f"Opening incident issue for {len(affected)} affected services.",
        },
        iteration,
    )
    yield AgentEvent(
        "tool_call",
        {"name": "create_incident_issue", "args": {"cve_id": event.cve_id}},
        iteration,
    )
    incident_issue = await gitlab.create_incident_issue(event=event, affected_count=len(affected))
    yield AgentEvent(
        "tool_result",
        {"name": incident_issue.name, "result": incident_issue.model_dump()},
        iteration,
    )

    merge_requests: list[dict[str, Any]] = []
    pipelines: list[dict[str, Any]] = []
    deployments: list[dict[str, Any]] = []

    for risk in affected:
        iteration += 1
        yield AgentEvent(
            "thought",
            {
                "text": (
                    f"{risk.service_name} scored {risk.risk_score}. "
                    "Opening a reviewable patch MR."
                ),
                "service_name": risk.service_name,
            },
            iteration,
        )

        yield AgentEvent(
            "tool_call",
            {
                "name": "create_patch_merge_request",
                "args": {"service_name": risk.service_name, "risk_score": risk.risk_score},
            },
            iteration,
        )
        mr = await gitlab.create_patch_merge_request(risk=risk, event=event)
        mr_payload = mr.model_dump()
        merge_requests.append(mr_payload)
        yield AgentEvent("tool_result", {"name": mr.name, "result": mr_payload}, iteration)

        yield AgentEvent(
            "tool_call",
            {"name": "run_security_pipeline", "args": {"service_name": risk.service_name}},
            iteration,
        )
        pipeline = await gitlab.run_security_pipeline(risk=risk)
        pipeline_payload = pipeline.model_dump()
        pipelines.append(pipeline_payload)
        yield AgentEvent(
            "tool_result",
            {"name": pipeline.name, "result": pipeline_payload},
            iteration,
        )

        if risk.auto_deploy_allowed and pipeline_payload["status"] == "passed":
            yield AgentEvent(
                "tool_call",
                {"name": "deploy_to_cloud_run", "args": {"service_name": risk.service_name}},
                iteration,
            )
            deployment = await gitlab.deploy_to_cloud_run(risk=risk)
            deployment_payload = deployment.model_dump()
            deployments.append(deployment_payload)
            yield AgentEvent(
                "tool_result",
                {"name": deployment.name, "result": deployment_payload},
                iteration,
            )

    summary = {
        "incident_title": event.incident_title,
        "cve_id": event.cve_id,
        "services_scanned": len(projects.payload.get("projects", [])),
        "services_affected": len(affected),
        "highest_risk_service": affected[0].service_name,
        "incident_issue": incident_issue.payload,
        "risk_ranking": [
            {
                "service_name": risk.service_name,
                "risk_score": risk.risk_score,
                "reason": risk.reason,
                "auto_deploy_allowed": risk.auto_deploy_allowed,
            }
            for risk in affected
        ],
        "merge_requests": merge_requests,
        "pipelines": pipelines,
        "deployments": deployments,
        "next_action": (
            "Request human approval for tier0 or high-risk services."
            if any(not risk.auto_deploy_allowed for risk in affected)
            else "All affected services are safe to patch automatically."
        ),
        "grounding_excerpt": grounding[:1200],
    }

    if settings.use_gemini_summary:
        try:
            summary["executive_summary"] = await _generate_executive_summary(
                settings=settings,
                event=event,
                summary=summary,
            )
        except Exception as exc:
            log.warning("agent_loop.gemini_summary_failed", exc_info=exc)
            summary["executive_summary"] = _fallback_executive_summary(summary)

    iteration += 1
    yield AgentEvent("final_report", summary, iteration)
    yield AgentEvent("done", {"reason": "incident_workflow_complete"}, iteration)


async def _generate_executive_summary(
    *,
    settings: Settings,
    event: VulnerabilityEvent,
    summary: dict[str, Any],
) -> str:
    prompt = f"""{prompts.SYSTEM_PROMPT}

You are writing a 3-sentence executive summary for a security incident.

CVE: {event.cve_id}
Title: {event.incident_title}
Package: {event.vulnerable_package} -> {event.fixed_version}
Affected services: {summary['services_affected']}
Highest risk: {summary['highest_risk_service']}
Deployments completed: {len(summary['deployments'])}
Next action: {summary['next_action']}

Write plainly for an engineering leader. No markdown bullets.
"""
    return await generate_text(settings=settings, prompt=prompt)


def _fallback_executive_summary(summary: dict[str, Any]) -> str:
    return (
        f"{summary['cve_id']} affected {summary['services_affected']} services. "
        f"Highest risk is {summary['highest_risk_service']}. "
        f"{summary['next_action']}"
    )
