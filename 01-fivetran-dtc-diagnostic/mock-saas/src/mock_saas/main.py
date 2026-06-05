"""Serve the synthetic VelvetMint data behind simple HTTP endpoints.

This gives us something concrete to point at while the real Fivetran trial is
still dormant. The shape is intentionally simple: one endpoint per
service/resource pair plus lightweight pagination and filtering.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query


@dataclass(frozen=True)
class DatasetSpec:
    """How to load and filter a synthetic dataset."""

    relative_path: str
    date_field: str | None = None
    date_kind: str | None = None



def default_synthetic_data_root() -> Path:
    """Resolve the checked-in dataset location for local development."""

    return Path(__file__).resolve().parents[4] / "synthetic-data"


SYNTHETIC_DATA_ROOT = Path(
    os.getenv("SYNTHETIC_DATA_ROOT", str(default_synthetic_data_root()))
)

DATASETS: dict[tuple[str, str], DatasetSpec] = {
    ("shopify", "orders"): DatasetSpec("shopify/orders.ndjson", "created_at", "iso-datetime"),
    ("shopify", "checkouts"): DatasetSpec("shopify/checkouts.ndjson", "created_at", "iso-datetime"),
    ("shopify", "customers"): DatasetSpec("shopify/customers.ndjson", "created_at", "iso-datetime"),
    ("klaviyo", "profiles"): DatasetSpec("klaviyo/profiles.ndjson", "created_at", "iso-datetime"),
    ("klaviyo", "campaigns"): DatasetSpec("klaviyo/campaigns.ndjson", "send_date", "iso-date"),
    ("klaviyo", "flows"): DatasetSpec("klaviyo/flows.ndjson", "updated_at", "iso-datetime"),
    ("meta-ads", "campaigns"): DatasetSpec("meta-ads/campaigns.ndjson"),
    ("meta-ads", "insights"): DatasetSpec("meta-ads/insights.ndjson", "date", "iso-date"),
    ("google-ads", "campaigns"): DatasetSpec("google-ads/campaigns.ndjson"),
    ("google-ads", "insights"): DatasetSpec("google-ads/insights.ndjson", "date", "iso-date"),
    ("tiktok-ads", "ads"): DatasetSpec("tiktok-ads/ads.ndjson"),
    ("tiktok-ads", "insights"): DatasetSpec("tiktok-ads/insights.ndjson", "date", "iso-date"),
    ("stripe", "charges"): DatasetSpec("stripe/charges.ndjson", "created", "unix-seconds"),
    ("stripe", "refunds"): DatasetSpec("stripe/refunds.ndjson", "created", "unix-seconds"),
    ("yotpo", "reviews"): DatasetSpec("yotpo/reviews.ndjson", "created_at", "iso-datetime"),
}

app = FastAPI(
    title="VelvetMint Mock SaaS Server",
    version="0.1.0",
    description=(
        "Tiny HTTP wrapper around the synthetic VelvetMint source data. Useful "
        "for local development and demo-mode playback before the live Fivetran "
        "trial is active."
    ),
)


@lru_cache(maxsize=None)
def load_dataset(service: str, resource: str) -> list[dict[str, Any]]:
    """Load one NDJSON dataset into memory."""

    spec = get_spec(service, resource)
    path = SYNTHETIC_DATA_ROOT / spec.relative_path
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def get_spec(service: str, resource: str) -> DatasetSpec:
    """Look up dataset metadata or raise a 404-like error."""

    spec = DATASETS.get((service, resource))
    if spec is None:
        raise KeyError(f"unknown dataset: {service}/{resource}")
    return spec


def parse_query_date(raw: str | None) -> date | None:
    """Accept YYYY-MM-DD in query params."""

    if raw is None:
        return None
    return date.fromisoformat(raw)


def record_date(record: dict[str, Any], spec: DatasetSpec) -> date | None:
    """Extract a comparable date from one record."""

    if spec.date_field is None or spec.date_kind is None:
        return None

    value = record.get(spec.date_field)
    if value is None:
        return None

    if spec.date_kind == "iso-date":
        return date.fromisoformat(str(value))
    if spec.date_kind == "iso-datetime":
        return datetime.fromisoformat(str(value)).date()
    if spec.date_kind == "unix-seconds":
        return datetime.fromtimestamp(int(value), tz=UTC).date()

    raise ValueError(f"unsupported date kind: {spec.date_kind}")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Cloud Run and local liveness check."""

    return {"status": "ok"}


@app.get("/datasets")
def list_datasets() -> dict[str, list[dict[str, Any]]]:
    """Return the available synthetic datasets."""

    items: list[dict[str, Any]] = []
    for (service, resource), spec in sorted(DATASETS.items()):
        items.append(
            {
                "service": service,
                "resource": resource,
                "path": spec.relative_path,
                "date_field": spec.date_field,
            }
        )
    return {"brand": "velvetmint", "datasets": items}


@app.get("/{service}/{resource}")
def get_records(
    service: str,
    resource: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    field: str | None = Query(default=None, description="Optional equality filter field."),
    value: str | None = Query(default=None, description="Optional equality filter value."),
) -> dict[str, Any]:
    """Return one synthetic dataset with optional filters and pagination."""

    try:
        spec = get_spec(service, resource)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    rows = load_dataset(service, resource)
    start = parse_query_date(start_date)
    end = parse_query_date(end_date)

    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_date = record_date(row, spec)
        if start and row_date and row_date < start:
            continue
        if end and row_date and row_date > end:
            continue
        if field and value is not None and str(row.get(field)) != value:
            continue
        filtered.append(row)

    page = filtered[offset : offset + limit]
    return {
        "brand": "velvetmint",
        "service": service,
        "resource": resource,
        "total": len(filtered),
        "returned": len(page),
        "offset": offset,
        "limit": limit,
        "items": page,
    }


def run() -> None:
    """Local entrypoint."""

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("mock_saas.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    run()
