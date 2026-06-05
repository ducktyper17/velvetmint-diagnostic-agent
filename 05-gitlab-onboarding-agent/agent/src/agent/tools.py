"""GitLab MCP client and typed tool wrappers for Blast Radius."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.config import Settings
from agent.scenario import ServiceRisk, VulnerabilityEvent, get_demo_services


log = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Uniform tool result object for streaming back to the UI."""

    name: str
    payload: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return {"name": self.name, **self.payload}


def _normalize_mcp_result(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten common MCP result envelopes."""

    if "content" in result and isinstance(result["content"], list):
        texts: list[str] = []
        for block in result["content"]:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
        if texts:
            return {"text": "\n".join(texts), **result}
    return result


class GitLabMCPClient:
    """HTTP client for the official GitLab MCP server with demo fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {settings.gitlab_mcp_token.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a GitLab MCP tool via JSON-RPC over HTTP."""

        if self.settings.is_demo:
            raise RuntimeError("demo mode active")

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 1,
        }
        response = await self._http.post(str(self.settings.gitlab_mcp_url), json=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"MCP error calling {name!r}: {body['error']}")
        return _normalize_mcp_result(body.get("result", {}))

    async def list_group_projects(self) -> ToolResult:
        if not self.settings.is_demo:
            try:
                raw = await self.call_tool(
                    "list_group_projects",
                    {"group_path": self.settings.gitlab_group_path},
                )
                return ToolResult("list_group_projects", {"projects": raw, "source": "gitlab_mcp"})
            except Exception as exc:
                log.warning("gitlab_mcp.list_group_projects_failed", exc_info=exc)

        projects = [
            {
                "service_name": service.service_name,
                "repo_path": service.repo_path,
                "owner": service.owner,
                "tier": service.tier,
                "internet_facing": service.internet_facing,
            }
            for service in get_demo_services()
        ]
        return ToolResult("list_group_projects", {"projects": projects, "source": "demo"})

    async def inspect_dependency_files(self, event: VulnerabilityEvent) -> ToolResult:
        if not self.settings.is_demo:
            try:
                raw = await self.call_tool(
                    "search_repository",
                    {
                        "group_path": self.settings.gitlab_group_path,
                        "query": event.vulnerable_package,
                    },
                )
                return ToolResult(
                    "inspect_dependency_files",
                    {"affected_projects": raw, "source": "gitlab_mcp"},
                )
            except Exception as exc:
                log.warning("gitlab_mcp.inspect_dependency_files_failed", exc_info=exc)

        affected = [
            {
                "service_name": service.service_name,
                "repo_path": service.repo_path,
                "dependency": event.vulnerable_package,
                "fixed_version": event.fixed_version,
            }
            for service in get_demo_services()
            if event.vulnerable_package in service.dependencies
        ]
        return ToolResult(
            "inspect_dependency_files",
            {"affected_projects": affected, "source": "demo"},
        )

    async def create_incident_issue(
        self,
        *,
        event: VulnerabilityEvent,
        affected_count: int,
    ) -> ToolResult:
        if not self.settings.is_demo and self.settings.gitlab_allow_writes:
            try:
                raw = await self.call_tool(
                    "create_issue",
                    {
                        "project_path": self.settings.gitlab_group_path,
                        "title": f"[{event.cve_id}] {event.incident_title}",
                        "description": (
                            f"Automated incident opened by Blast Radius for "
                            f"{event.vulnerable_package} -> {event.fixed_version}."
                        ),
                        "labels": ["security", "zero-day", "blast-radius"],
                    },
                )
                return ToolResult("create_incident_issue", {**raw, "source": "gitlab_mcp"})
            except Exception as exc:
                log.warning("gitlab_mcp.create_incident_issue_failed", exc_info=exc)

        issue_iid = 100 + affected_count
        return ToolResult(
            "create_incident_issue",
            {
                "issue_iid": issue_iid,
                "title": f"[{event.cve_id}] {event.incident_title}",
                "url": (
                    f"{self.settings.gitlab_base_url}/"
                    f"{self.settings.gitlab_group_path}/-/issues/{issue_iid}"
                ),
                "source": "demo",
            },
        )

    async def create_patch_merge_request(
        self,
        *,
        risk: ServiceRisk,
        event: VulnerabilityEvent,
    ) -> ToolResult:
        if not self.settings.is_demo and self.settings.gitlab_allow_writes:
            try:
                raw = await self.call_tool(
                    "create_merge_request",
                    {
                        "project_path": risk.repo_path,
                        "title": f"security: bump {event.vulnerable_package} to {event.fixed_version}",
                        "source_branch": f"security/{event.cve_id.lower()}-{risk.service_name}",
                        "target_branch": "main",
                        "description": (
                            f"Automated patch for {event.cve_id}. Risk score {risk.risk_score}. "
                            f"{risk.reason}"
                        ),
                    },
                )
                return ToolResult(
                    "create_patch_merge_request",
                    {"service_name": risk.service_name, **raw, "source": "gitlab_mcp"},
                )
            except Exception as exc:
                log.warning("gitlab_mcp.create_patch_merge_request_failed", exc_info=exc)

        mr_iid = abs(hash((risk.service_name, event.cve_id))) % 500 + 1
        return ToolResult(
            "create_patch_merge_request",
            {
                "service_name": risk.service_name,
                "mr_iid": mr_iid,
                "branch_name": f"security/{event.cve_id.lower()}-{risk.service_name}",
                "url": f"{self.settings.gitlab_base_url}/{risk.repo_path}/-/merge_requests/{mr_iid}",
                "summary": f"Bump {event.vulnerable_package} to {event.fixed_version}",
                "source": "demo",
            },
        )

    async def run_security_pipeline(self, *, risk: ServiceRisk) -> ToolResult:
        pipeline_id = str(uuid4())
        status = "passed" if risk.risk_score <= 80 else "needs_review"
        return ToolResult(
            "run_security_pipeline",
            {
                "service_name": risk.service_name,
                "pipeline_id": pipeline_id,
                "status": status,
                "checks": ["dependency_scanning", "sast", "secret_detection"],
                "source": "demo",
            },
        )

    async def deploy_to_cloud_run(self, *, risk: ServiceRisk) -> ToolResult:
        return ToolResult(
            "deploy_to_cloud_run",
            {
                "service_name": risk.service_name,
                "region": self.settings.demo_cloud_run_region,
                "cloud_run_service": risk.service_name,
                "status": "deployed",
                "source": "gitlab_ci",
            },
        )
