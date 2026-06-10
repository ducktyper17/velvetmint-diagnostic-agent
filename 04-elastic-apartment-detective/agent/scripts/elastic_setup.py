"""Provision the four Elastic indices the Apartment Detective relies on.

Run once against a fresh Elastic Cloud Serverless project:

    source .venv/bin/activate
    uv pip install -e ".[ingest]"
    export ELASTIC_ENDPOINT="https://<project>.es.<region>.elastic.cloud:443"
    export ELASTIC_API_KEY="<base64 api key with manage privileges>"
    python scripts/elastic_setup.py

Indices:
  - hpd_violations      building-level housing violations (ES|QL structured)
  - nyc_311             nearby quality-of-life complaints (ES|QL structured)
  - tenant_signal_docs  curated tenant chatter (hybrid: ELSER semantic_text)
  - building_briefs     agent memory — normalized briefs written back by the agent

The tenant_signal_docs mapping uses `semantic_text`, which makes Elastic run
ELSER automatically on ingest and at query time — that is what powers the
hybrid (semantic + keyword) search the agent calls `search_tenant_sentiment`.
"""

from __future__ import annotations

import os
import sys

from elasticsearch import Elasticsearch

# A keyword address + geo_point shows up in every index so the ES|QL tools can
# filter by exact building and by radius around the listing.
_COMMON_LOCATION = {
    "address": {"type": "keyword"},
    "borough": {"type": "keyword"},
    "zip": {"type": "keyword"},
    "location": {"type": "geo_point"},
}

INDEX_MAPPINGS: dict[str, dict] = {
    "hpd_violations": {
        "mappings": {
            "properties": {
                **_COMMON_LOCATION,
                "violation_id": {"type": "keyword"},
                "category": {"type": "keyword"},
                "severity_class": {"type": "keyword"},  # A / B / C (C = most severe)
                "status": {"type": "keyword"},  # open / closed
                "description": {"type": "text"},
                "reported_at": {"type": "date"},
            }
        }
    },
    "nyc_311": {
        "mappings": {
            "properties": {
                **_COMMON_LOCATION,
                "complaint_id": {"type": "keyword"},
                "complaint_type": {"type": "keyword"},
                "descriptor": {"type": "keyword"},
                "hour_of_day": {"type": "integer"},  # for the late-night noise share
                "created_at": {"type": "date"},
            }
        }
    },
    "tenant_signal_docs": {
        "mappings": {
            "properties": {
                **_COMMON_LOCATION,
                "source": {"type": "keyword"},  # reddit / local-news
                "url": {"type": "keyword"},
                "title": {"type": "text"},
                # semantic_text => ELSER runs automatically on ingest + query.
                "body": {"type": "semantic_text", "inference_id": ".elser-2-elasticsearch"},
                "posted_at": {"type": "date"},
            }
        }
    },
    "building_briefs": {
        "mappings": {
            "properties": {
                **_COMMON_LOCATION,
                "risk_score": {"type": "float"},
                "summary": {"type": "text"},
                "top_red_flags": {"type": "keyword"},
                "evidence": {"type": "text"},
                "updated_at": {"type": "date"},
            }
        }
    },
}


def client() -> Elasticsearch:
    """Build an Elasticsearch client from env vars."""

    endpoint = os.environ.get("ELASTIC_ENDPOINT")
    api_key = os.environ.get("ELASTIC_API_KEY")
    if not endpoint or not api_key:
        print("Set ELASTIC_ENDPOINT and ELASTIC_API_KEY first.")
        raise SystemExit(1)
    return Elasticsearch(endpoint, api_key=api_key, request_timeout=60)


def main() -> int:
    """Create each index if it does not already exist."""

    es = client()
    for name, body in INDEX_MAPPINGS.items():
        if es.indices.exists(index=name):
            print(f"= {name} already exists; leaving it in place")
            continue
        es.indices.create(index=name, **body)
        print(f"+ created {name}")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
