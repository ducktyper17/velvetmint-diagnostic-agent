"""Seed the curated tenant-sentiment corpus into Elastic for hybrid search.

The corpus is small and high-signal on purpose: a handful of Reddit/local-news
style posts (including the demo building at 123 Orchard St) that read like
indirect complaints. Indexing them into the `semantic_text` field makes Elastic
run ELSER automatically, so `search_tenant_sentiment` retrieves them by meaning,
not just keywords — e.g. a query about "noise at night" surfaces the
"paper-thin walls / bar two doors down" post.

    source .venv/bin/activate
    uv pip install -e ".[ingest]"
    export ELASTIC_ENDPOINT=... ELASTIC_API_KEY=...
    python scripts/seed_tenant_signals.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from elasticsearch import helpers

from scripts.elastic_setup import client

CORPUS = Path(__file__).resolve().parent.parent / "data" / "tenant_signals.json"


def main() -> int:
    docs = json.loads(CORPUS.read_text(encoding="utf-8"))
    es = client()
    actions = [
        {"_index": "tenant_signal_docs", "_id": doc["url"], "_source": doc} for doc in docs
    ]
    ok, errors = helpers.bulk(es, actions, raise_on_error=False)
    n_err = len(errors) if isinstance(errors, list) else errors
    print(f"+ tenant_signal_docs: indexed {ok}, errors {n_err}")
    print("note: ELSER inference runs on ingest; first query may warm the model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
