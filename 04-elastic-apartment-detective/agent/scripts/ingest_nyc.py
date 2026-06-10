"""Load real NYC Open Data (HPD violations + 311) into Elastic.

Pulls from NYC's public Socrata API — no API token required for the modest
volumes we need. Scope is deliberately narrow (a few Lower East Side ZIPs that
include the demo building) so the demo stays fast and the indices stay small.

    source .venv/bin/activate
    uv pip install -e ".[ingest]"
    export ELASTIC_ENDPOINT="https://<project>.es.<region>.elastic.cloud:443"
    export ELASTIC_API_KEY="<base64 api key>"
    python scripts/ingest_nyc.py --zips 10002,10009 --limit 5000

Datasets:
  - HPD violations:  https://data.cityofnewyork.us/resource/wvxf-dwi5.json
  - 311 requests:    https://data.cityofnewyork.us/resource/erm2-nwe9.json
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from typing import Any

import httpx
from elasticsearch import Elasticsearch, helpers

from scripts.elastic_setup import client

HPD_URL = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
NYC311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

# 311 complaint types that matter to a renter; keeps the index focused.
RELEVANT_311 = (
    "Noise",
    "Noise - Residential",
    "Noise - Commercial",
    "HEAT/HOT WATER",
    "Rodent",
    "Unsanitary Condition",
    "Plumbing",
    "PAINT/PLASTER",
    "Illegal Parking",
)


def _fetch(url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    resp = httpx.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def hpd_docs(zips: list[str], limit: int) -> Iterator[dict[str, Any]]:
    """Yield Elastic bulk actions for HPD violations in the given ZIPs."""

    zip_clause = " OR ".join(f"zip='{z}'" for z in zips)
    rows = _fetch(
        HPD_URL,
        {
            "$where": f"({zip_clause})",
            "$limit": limit,
            "$order": "inspectiondate DESC",
        },
    )
    for r in rows:
        house = (r.get("housenumber") or "").strip()
        street = (r.get("streetname") or "").strip()
        address = f"{house} {street}".strip()
        if not address:
            continue
        yield {
            "_index": "hpd_violations",
            "_id": r.get("violationid"),
            "_source": {
                "violation_id": r.get("violationid"),
                "address": address.title(),
                "borough": (r.get("boro") or "").title() or None,
                "zip": r.get("zip"),
                "category": r.get("class") and f"class {r['class']}",
                "severity_class": r.get("class"),
                "status": "open" if (r.get("violationstatus") == "Open") else "closed",
                "description": r.get("novdescription"),
                "reported_at": r.get("inspectiondate"),
            },
        }


def nyc311_docs(zips: list[str], limit: int) -> Iterator[dict[str, Any]]:
    """Yield Elastic bulk actions for relevant 311 complaints in the given ZIPs."""

    zip_clause = " OR ".join(f"incident_zip='{z}'" for z in zips)
    type_clause = " OR ".join(f"complaint_type='{t}'" for t in RELEVANT_311)
    rows = _fetch(
        NYC311_URL,
        {
            "$where": f"({zip_clause}) AND ({type_clause})",
            "$limit": limit,
            "$order": "created_date DESC",
        },
    )
    for r in rows:
        address = (r.get("incident_address") or "").strip()
        if not address:
            continue
        created = r.get("created_date")
        hour = int(created[11:13]) if created and len(created) >= 13 else None
        lat, lon = r.get("latitude"), r.get("longitude")
        yield {
            "_index": "nyc_311",
            "_id": r.get("unique_key"),
            "_source": {
                "complaint_id": r.get("unique_key"),
                "address": address.title(),
                "borough": (r.get("borough") or "").title() or None,
                "zip": r.get("incident_zip"),
                "complaint_type": r.get("complaint_type"),
                "descriptor": r.get("descriptor"),
                "hour_of_day": hour,
                "created_at": created,
                "location": {"lat": float(lat), "lon": float(lon)} if lat and lon else None,
            },
        }


def _load(es: Elasticsearch, actions: Iterator[dict[str, Any]], label: str) -> None:
    ok, errors = helpers.bulk(es, actions, raise_on_error=False, stats_only=False)
    n_err = len(errors) if isinstance(errors, list) else errors
    print(f"+ {label}: indexed {ok}, errors {n_err}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest NYC HPD + 311 into Elastic.")
    parser.add_argument("--zips", default="10002,10009", help="comma-separated ZIPs")
    parser.add_argument("--limit", type=int, default=5000, help="max rows per dataset")
    args = parser.parse_args()

    zips = [z.strip() for z in args.zips.split(",") if z.strip()]
    es = client()
    print(f"loading HPD + 311 for ZIPs {zips} (limit {args.limit} each)…")
    _load(es, hpd_docs(zips, args.limit), "hpd_violations")
    _load(es, nyc311_docs(zips, args.limit), "nyc_311")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
