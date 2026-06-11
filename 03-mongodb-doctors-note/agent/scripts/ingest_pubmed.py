"""Build a real literature corpus from PubMed via NCBI E-utilities.

This replaces the hand-written sample abstracts with genuine published
abstracts, so the Atlas knowledge base is credible rather than a toy. It
uses only the Python standard library (no API key required for low volume),
writes the result to `agent/corpus/literature.json`, and `seed_data.py`
prefers that file when present.

Usage:
    python scripts/ingest_pubmed.py                 # default conditions
    python scripts/ingest_pubmed.py --per 8         # more per condition

Be a good API citizen: E-utilities asks for <=3 requests/sec without a key,
so we sleep between calls. See:
https://www.ncbi.nlm.nih.gov/books/NBK25497/
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Each condition maps to a focused query that surfaces base-rate / management
# literature (what a patient actually needs), not bench science.
CONDITION_QUERIES: dict[str, str] = {
    "thyroid_nodule": "thyroid nodule TI-RADS malignancy risk management",
    "lung_nodule": "incidental pulmonary nodule Fleischner malignancy risk surveillance",
    "breast_mass": "breast BI-RADS 3 probably benign malignancy rate follow-up",
    "cbc_abnormality": "incidental anemia adults evaluation primary care",
}

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "doctors-note-decoder/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted host)
        return resp.read()


def _esearch(query: str, retmax: int) -> list[str]:
    params = urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json", "sort": "relevance"}
    )
    data = json.loads(_get(f"{EUTILS}/esearch.fcgi?{params}"))
    return data.get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"}
    )
    root = ET.fromstring(_get(f"{EUTILS}/efetch.fcgi?{params}"))
    out: list[dict] = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID") or ""
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        abstract = " ".join(
            "".join(node.itertext()).strip() for node in art.findall(".//AbstractText")
        ).strip()
        year = art.findtext(".//JournalIssue/PubDate/Year") or art.findtext(".//PubDate/Year")
        if not (title and abstract):
            continue
        out.append(
            {
                "pmid": pmid,
                "title": title.strip(),
                "abstract": abstract,
                "published_year": int(year) if year and year.isdigit() else None,
            }
        )
    return out


def build_corpus(per_condition: int) -> list[dict]:
    docs: list[dict] = []
    for condition, query in CONDITION_QUERIES.items():
        print(f"[ingest] {condition}: searching PubMed…", file=sys.stderr)
        pmids = _esearch(query, per_condition)
        time.sleep(0.4)
        for art in _efetch(pmids):
            docs.append(
                {
                    "_id": f"pubmed-{art['pmid']}",
                    "title": art["title"],
                    "abstract": art["abstract"],
                    "condition": condition,
                    # Literature is not filtered by severity at retrieval time,
                    # so we leave it unset rather than guess a tier per paper.
                    "severity_tier": None,
                    "source": "pubmed",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/",
                    "published_year": art["published_year"],
                    "language": "en",
                    "is_sample": False,
                }
            )
        time.sleep(0.4)
        print(f"[ingest] {condition}: {len(pmids)} hits", file=sys.stderr)
    return docs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=6, help="abstracts per condition")
    args = ap.parse_args()

    docs = build_corpus(args.per)
    CORPUS_DIR.mkdir(exist_ok=True)
    out_path = CORPUS_DIR / "literature.json"
    out_path.write_text(json.dumps(docs, indent=2), encoding="utf-8")
    print(f"[ingest] wrote {len(docs)} real PubMed abstracts -> {out_path}")
    print("[ingest] now run `python seed_data.py` to embed + upload to Atlas.")


if __name__ == "__main__":
    main()
