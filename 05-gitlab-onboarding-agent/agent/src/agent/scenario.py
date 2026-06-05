"""Demo scenario data and risk-scoring helpers for Blast Radius."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ServiceTier = Literal["tier0", "tier1", "tier2"]


@dataclass(frozen=True)
class ServiceRecord:
    """Represents one service in the demo GitLab group."""

    service_name: str
    repo_path: str
    owner: str
    tier: ServiceTier
    internet_facing: bool
    auto_deploy_enabled: bool
    cloud_run_service: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class VulnerabilityEvent:
    """Input signal that starts the incident response flow."""

    incident_title: str
    cve_id: str
    vulnerable_package: str
    fixed_version: str


@dataclass(frozen=True)
class ServiceRisk:
    """Computed blast-radius result for one service."""

    service_name: str
    repo_path: str
    owner: str
    tier: ServiceTier
    internet_facing: bool
    risk_score: int
    fix_available: bool
    auto_deploy_allowed: bool
    reason: str


DEMO_SERVICES: tuple[ServiceRecord, ...] = (
    ServiceRecord(
        service_name="checkout-service",
        repo_path="rapid-agent-labs/checkout-service",
        owner="payments@rapid-agent.dev",
        tier="tier0",
        internet_facing=True,
        auto_deploy_enabled=False,
        cloud_run_service="checkout-service",
        dependencies=("fastify", "log4js", "stripe"),
    ),
    ServiceRecord(
        service_name="user-service",
        repo_path="rapid-agent-labs/user-service",
        owner="identity@rapid-agent.dev",
        tier="tier1",
        internet_facing=True,
        auto_deploy_enabled=False,
        cloud_run_service="user-service",
        dependencies=("fastify", "log4js", "pg"),
    ),
    ServiceRecord(
        service_name="analytics-worker",
        repo_path="rapid-agent-labs/analytics-worker",
        owner="data@rapid-agent.dev",
        tier="tier2",
        internet_facing=False,
        auto_deploy_enabled=True,
        cloud_run_service="analytics-worker",
        dependencies=("bullmq", "log4js", "bigquery"),
    ),
    ServiceRecord(
        service_name="marketing-site",
        repo_path="rapid-agent-labs/marketing-site",
        owner="growth@rapid-agent.dev",
        tier="tier2",
        internet_facing=True,
        auto_deploy_enabled=True,
        cloud_run_service="marketing-site",
        dependencies=("next", "segment"),
    ),
    ServiceRecord(
        service_name="support-bff",
        repo_path="rapid-agent-labs/support-bff",
        owner="support-platform@rapid-agent.dev",
        tier="tier1",
        internet_facing=False,
        auto_deploy_enabled=False,
        cloud_run_service="support-bff",
        dependencies=("fastify", "redis"),
    ),
)


def get_demo_services() -> tuple[ServiceRecord, ...]:
    """Return the static service catalog used by the demo."""

    return DEMO_SERVICES


def get_default_vulnerability() -> VulnerabilityEvent:
    """Return the default vulnerability scenario used by the API."""

    return VulnerabilityEvent(
        incident_title="Critical log4js vulnerability",
        cve_id="CVE-2026-4242",
        vulnerable_package="log4js",
        fixed_version="6.9.1",
    )


def compute_service_risk(
    service: ServiceRecord,
    event: VulnerabilityEvent,
    *,
    auto_deploy_max_risk: int,
) -> ServiceRisk | None:
    """Return a scored service risk if the service is affected."""

    if event.vulnerable_package not in service.dependencies:
        return None

    score = 25
    reasons: list[str] = [f"depends on {event.vulnerable_package}"]

    if service.internet_facing:
        score += 20
        reasons.append("internet-facing")

    tier_weight = {"tier0": 35, "tier1": 20, "tier2": 10}[service.tier]
    score += tier_weight
    reasons.append(service.tier)

    if service.service_name == "checkout-service":
        score += 10
        reasons.append("revenue path")

    if service.auto_deploy_enabled:
        score -= 5
        reasons.append("safe deploy path exists")

    score = max(1, min(100, score))
    auto_deploy_allowed = service.auto_deploy_enabled and score <= auto_deploy_max_risk

    return ServiceRisk(
        service_name=service.service_name,
        repo_path=service.repo_path,
        owner=service.owner,
        tier=service.tier,
        internet_facing=service.internet_facing,
        risk_score=score,
        fix_available=True,
        auto_deploy_allowed=auto_deploy_allowed,
        reason=", ".join(reasons),
    )


def rank_affected_services(
    event: VulnerabilityEvent,
    *,
    auto_deploy_max_risk: int,
) -> list[ServiceRisk]:
    """Rank affected services from highest to lowest risk."""

    affected: list[ServiceRisk] = []
    for service in get_demo_services():
        result = compute_service_risk(
            service,
            event,
            auto_deploy_max_risk=auto_deploy_max_risk,
        )
        if result is not None:
            affected.append(result)

    return sorted(affected, key=lambda item: item.risk_score, reverse=True)
