"""Diagnostic engine: cross-platform analytical queries over Fivetran data.

Given the brand's Fivetran-synced tables in BigQuery, this module runs a
fixed battery of ~12 diagnostic queries and returns ranked
:class:`Finding` objects. The agent loop calls
:func:`run_named_query` (one metric at a time) and
:func:`run_battery` (all twelve in parallel).

Why "named queries" and not free-form SQL: the agent should not write SQL.
We curate the queries here, version them, and trust them. The agent only
chooses *which* metric to investigate.

The actual SQL bodies are stubbed below — they will be filled in during
Day 7 of the build plan, when the seeded VelvetMint dataset exists in
BigQuery and the schemas are known.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

from agent.config import get_settings


log = logging.getLogger(__name__)


Confidence = Literal["low", "medium", "high"]
Category = Literal["acquisition", "retention", "conversion", "fulfillment", "other"]


@dataclass(frozen=True)
class Finding:
    """One ranked anomaly with a suggested fix.

    ``revenue_impact_usd`` is a monthly-equivalent estimate; the diagnostic
    engine annualizes inside each query.
    """

    title: str
    category: Category
    metric: str
    current_value: float
    baseline_value: float
    delta_pct: float
    revenue_impact_usd: float
    confidence: Confidence
    root_cause: str
    recommended_fix: str
    evidence: str


# Catalog of supported metric names. Keep this list in lockstep with the
# agent system prompt so Gemini cannot ask for a metric we do not implement.
SUPPORTED_METRICS: tuple[str, ...] = (
    "roas_by_channel",
    "email_engagement_decay",
    "funnel_conv_by_browser",
    "refund_rate",
    "creative_fatigue_by_ad",
    "paid_vs_organic_mix",
    "aov_by_segment",
    "ltv_by_acquisition_channel",
    "return_rate",
    "dispute_rate",
    "inventory_velocity",
    "review_sentiment_trend",
)


async def run_named_query(
    *,
    metric: str,
    window_days: int,
    brand_id: str,
) -> list[dict[str, Any]]:
    """Execute one diagnostic query and return its rows.

    Args:
        metric: one of :data:`SUPPORTED_METRICS`.
        window_days: lookback window. 30, 60, 90, or 180.
        brand_id: which brand's BigQuery sub-dataset to read.
    """
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"unknown metric {metric!r}; expected one of {SUPPORTED_METRICS}")
    settings = get_settings()

    # TODO: replace with a real BigQuery client call. Day 7 of the build plan
    # implements these. The expected shape is:
    #
    #     from google.cloud import bigquery
    #     client = bigquery.Client(
    #         project=settings.google_cloud_project,
    #         location=settings.bigquery_location,
    #     )
    #     sql = _SQL_BY_METRIC[metric].format(
    #         dataset=settings.bigquery_dataset,
    #         window_days=window_days,
    #     )
    #     return [dict(row) for row in client.query(sql).result()]

    log.info(
        "diagnostic.run_named_query",
        extra={
            "metric": metric,
            "window_days": window_days,
            "brand_id": brand_id,
            "stub": True,
        },
    )
    _ = settings  # avoid "unused" until we wire BigQuery in
    return _stub_rows_for(metric)


async def run_battery(*, brand_id: str) -> list[Finding]:
    """Run every supported diagnostic query in parallel and rank the results.

    Returns the top 3 :class:`Finding` objects by absolute dollar impact. The
    agent loop hands these to :func:`agent.tools` ``finalize_diagnosis``.
    """
    tasks = [
        run_named_query(metric=m, window_days=90, brand_id=brand_id)
        for m in SUPPORTED_METRICS
    ]
    rows_per_metric = await asyncio.gather(*tasks, return_exceptions=True)

    findings: list[Finding] = []
    for metric, result in zip(SUPPORTED_METRICS, rows_per_metric, strict=True):
        if isinstance(result, BaseException):
            log.warning("diagnostic.metric_failed", extra={"metric": metric, "err": str(result)})
            continue
        f = _interpret_rows(metric=metric, rows=result)
        if f is not None:
            findings.append(f)

    findings.sort(key=lambda f: abs(f.revenue_impact_usd), reverse=True)
    return findings[:3]


# ---------------------------------------------------------------------------
# Stubs — replaced during Day 7 of the build plan.
# ---------------------------------------------------------------------------


def _stub_rows_for(metric: str) -> list[dict[str, Any]]:
    """Hard-coded rows so the agent loop can be exercised end-to-end before
    BigQuery is wired up. These align with the seeded VelvetMint anomalies
    used in the demo script.
    """
    if metric == "roas_by_channel":
        return [
            {"channel": "tiktok_ads", "roas_current": 0.9, "roas_baseline": 1.6, "spend_usd": 28000},
            {"channel": "meta_ads", "roas_current": 1.8, "roas_baseline": 1.9, "spend_usd": 22000},
            {"channel": "google_ads", "roas_current": 2.1, "roas_baseline": 2.1, "spend_usd": 11000},
        ]
    if metric == "email_engagement_decay":
        return [
            {"week_iso": "2026-W18", "open_rate": 0.246, "subs_added": 312},
            {"week_iso": "2026-W19", "open_rate": 0.211, "subs_added": 41},
            {"week_iso": "2026-W20", "open_rate": 0.201, "subs_added": 38},
        ]
    if metric == "funnel_conv_by_browser":
        return [
            {"browser": "ios_safari", "conv_current": 0.018, "conv_baseline": 0.023},
            {"browser": "chrome", "conv_current": 0.022, "conv_baseline": 0.023},
            {"browser": "firefox", "conv_current": 0.021, "conv_baseline": 0.022},
        ]
    return []


def _interpret_rows(*, metric: str, rows: list[dict[str, Any]]) -> Finding | None:
    """Convert raw query rows into a :class:`Finding`.

    This is the "rules engine" layer between BigQuery output and a structured
    diagnosis. Rules are intentionally simple — the LLM is what makes the
    final call about *why*; this layer just surfaces *what* moved.

    Returns None if the metric did not show a material anomaly.
    """
    # TODO: implement per-metric interpretation. The three below match the
    # demo script and are enough to ship the v0.

    if metric == "roas_by_channel" and rows:
        worst = min(rows, key=lambda r: r["roas_current"] / max(r["roas_baseline"], 0.01))
        delta = (worst["roas_current"] - worst["roas_baseline"]) / max(worst["roas_baseline"], 0.01)
        if delta > -0.20:
            return None
        impact = -delta * float(worst["spend_usd"])
        return Finding(
            title=f"{worst['channel']} ROAS dropped {abs(delta) * 100:.0f}%",
            category="acquisition",
            metric=metric,
            current_value=float(worst["roas_current"]),
            baseline_value=float(worst["roas_baseline"]),
            delta_pct=float(delta),
            revenue_impact_usd=float(impact),
            confidence="high",
            root_cause="Top creatives are stale; CTR has been falling for 4+ weeks.",
            recommended_fix="Pause the bottom-decile creatives; launch 2 new variants this week.",
            evidence=f"channel-level ROAS over 90 days; spend ${worst['spend_usd']:,.0f}/mo",
        )

    if metric == "email_engagement_decay" and rows:
        latest = rows[-1]
        first = rows[0]
        delta = (latest["subs_added"] - first["subs_added"]) / max(first["subs_added"], 1)
        if delta > -0.40:
            return None
        return Finding(
            title="Email signups collapsed (popup likely broken)",
            category="retention",
            metric=metric,
            current_value=float(latest["subs_added"]),
            baseline_value=float(first["subs_added"]),
            delta_pct=float(delta),
            revenue_impact_usd=11_200.0,  # TODO: compute from cohort LTV when real
            confidence="medium",
            root_cause="Klaviyo signup events fell ~87% week over week; signup popup is likely failing on mobile.",
            recommended_fix="Repair popup; backfill subscribers from Shopify checkout email opt-ins.",
            evidence=f"{first['subs_added']} -> {latest['subs_added']} weekly subscribers",
        )

    if metric == "funnel_conv_by_browser" and rows:
        worst = min(rows, key=lambda r: r["conv_current"] / max(r["conv_baseline"], 0.0001))
        delta = (worst["conv_current"] - worst["conv_baseline"]) / max(worst["conv_baseline"], 0.0001)
        if delta > -0.15:
            return None
        return Finding(
            title=f"{worst['browser']} checkout conversion dropped {abs(delta) * 100:.0f}%",
            category="conversion",
            metric=metric,
            current_value=float(worst["conv_current"]),
            baseline_value=float(worst["conv_baseline"]),
            delta_pct=float(delta),
            revenue_impact_usd=7_800.0,  # TODO: compute from sessions x AOV when real
            confidence="high",
            root_cause="Recent Shopify theme deploy introduced a checkout JS error on this browser.",
            recommended_fix="Roll back the offending theme commit or wrap the Apple Pay handler in try/catch.",
            evidence=f"{worst['browser']} conv {worst['conv_baseline']:.3f} -> {worst['conv_current']:.3f}",
        )

    return None
