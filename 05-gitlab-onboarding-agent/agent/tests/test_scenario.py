from __future__ import annotations

from agent.scenario import get_default_vulnerability, rank_affected_services


def test_rank_affected_services_orders_by_risk() -> None:
    event = get_default_vulnerability()
    ranked = rank_affected_services(event, auto_deploy_max_risk=74)
    assert len(ranked) == 3
    assert ranked[0].service_name == "checkout-service"
    assert ranked[0].risk_score >= ranked[-1].risk_score
