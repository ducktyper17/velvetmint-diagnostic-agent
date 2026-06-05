"""Typed wrappers around the Elastic Agent Builder MCP tool surface."""

from __future__ import annotations

import re
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.config import Settings


class BuildingMemory(BaseModel):
    """Prior normalized knowledge stored for a building."""

    address: str
    found: bool
    summary: str | None = None
    prior_risk_score: float | None = None
    prior_flags: list[str] = Field(default_factory=list)


class HPDViolations(BaseModel):
    """Structured HPD result."""

    address: str
    open_violations: int
    severe_categories: list[str] = Field(default_factory=list)
    recent_examples: list[str] = Field(default_factory=list)


class ComplaintSignals(BaseModel):
    """Structured 311 signal summary."""

    address: str
    complaint_count_90d: int
    top_categories: list[str] = Field(default_factory=list)
    nighttime_noise_share: float


class TenantSentiment(BaseModel):
    """Unstructured text evidence surfaced through hybrid retrieval."""

    address: str
    mentions_found: int
    highlights: list[str] = Field(default_factory=list)


class NeighborhoodComparison(BaseModel):
    """How this address compares with a nearby baseline."""

    address: str
    complaint_index_vs_zip: float
    summary: str


class SavedBrief(BaseModel):
    """Result of writing a building brief back into Elastic."""

    address: str
    stored: bool
    document_id: str


class ElasticMCPClient:
    """Tiny JSON-RPC client for Elastic Agent Builder MCP."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        )

    async def aclose(self) -> None:
        """Close the shared HTTP client."""

        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one Elastic MCP tool and return the JSON-RPC result body."""

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 1,
        }
        response = await self._client.post(
            str(self._settings.elastic_mcp_url),
            headers={
                "Authorization": f"ApiKey {self._settings.elastic_mcp_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"Elastic MCP error calling {name!r}: {body['error']}")
        return body.get("result", {})


async def search_building_memory(
    client: ElasticMCPClient,
    *,
    address: str,
) -> BuildingMemory:
    """Look up prior building summaries in Elastic or return demo data."""

    if client._settings.is_demo:
        sample = _sample_payload(address)
        return BuildingMemory(
            address=sample["address"],
            found=sample["memory"]["found"],
            summary=sample["memory"]["summary"],
            prior_risk_score=sample["memory"]["prior_risk_score"],
            prior_flags=list(sample["memory"]["prior_flags"]),
        )

    result = await client.call_tool("search_building_memory", {"address": address})
    return BuildingMemory(
        address=address,
        found=bool(result.get("found")),
        summary=result.get("summary"),
        prior_risk_score=_coerce_float(result.get("prior_risk_score")),
        prior_flags=_coerce_list(result.get("prior_flags")),
    )


async def get_hpd_violations(
    client: ElasticMCPClient,
    *,
    address: str,
) -> HPDViolations:
    """Fetch HPD-style building violations."""

    if client._settings.is_demo:
        sample = _sample_payload(address)
        return HPDViolations(
            address=sample["address"],
            open_violations=sample["hpd"]["open_violations"],
            severe_categories=list(sample["hpd"]["severe_categories"]),
            recent_examples=list(sample["hpd"]["recent_examples"]),
        )

    result = await client.call_tool("get_hpd_violations", {"address": address})
    return HPDViolations(
        address=address,
        open_violations=int(result.get("open_violations", 0)),
        severe_categories=_coerce_list(result.get("severe_categories")),
        recent_examples=_coerce_list(result.get("recent_examples")),
    )


async def get_311_signals(
    client: ElasticMCPClient,
    *,
    address: str,
) -> ComplaintSignals:
    """Fetch nearby complaint signals."""

    if client._settings.is_demo:
        sample = _sample_payload(address)
        return ComplaintSignals(
            address=sample["address"],
            complaint_count_90d=sample["signals"]["complaint_count_90d"],
            top_categories=list(sample["signals"]["top_categories"]),
            nighttime_noise_share=sample["signals"]["nighttime_noise_share"],
        )

    result = await client.call_tool("get_311_signals", {"address": address})
    return ComplaintSignals(
        address=address,
        complaint_count_90d=int(result.get("complaint_count_90d", 0)),
        top_categories=_coerce_list(result.get("top_categories")),
        nighttime_noise_share=_coerce_float(result.get("nighttime_noise_share"), default=0.0),
    )


async def search_tenant_sentiment(
    client: ElasticMCPClient,
    *,
    address: str,
) -> TenantSentiment:
    """Run hybrid retrieval over tenant-signal documents."""

    if client._settings.is_demo:
        sample = _sample_payload(address)
        return TenantSentiment(
            address=sample["address"],
            mentions_found=sample["sentiment"]["mentions_found"],
            highlights=list(sample["sentiment"]["highlights"]),
        )

    result = await client.call_tool("search_tenant_sentiment", {"address": address})
    return TenantSentiment(
        address=address,
        mentions_found=int(result.get("mentions_found", 0)),
        highlights=_coerce_list(result.get("highlights")),
    )


async def compare_to_neighborhood_baseline(
    client: ElasticMCPClient,
    *,
    address: str,
) -> NeighborhoodComparison:
    """Compare this address to a neighborhood complaint baseline."""

    if client._settings.is_demo:
        sample = _sample_payload(address)
        return NeighborhoodComparison(
            address=sample["address"],
            complaint_index_vs_zip=sample["baseline"]["complaint_index_vs_zip"],
            summary=sample["baseline"]["summary"],
        )

    result = await client.call_tool("compare_to_neighborhood_baseline", {"address": address})
    return NeighborhoodComparison(
        address=address,
        complaint_index_vs_zip=_coerce_float(result.get("complaint_index_vs_zip"), default=1.0),
        summary=str(result.get("summary", "")),
    )


async def save_building_brief(
    client: ElasticMCPClient,
    *,
    address: str,
    risk_score: float,
    summary: str,
) -> SavedBrief:
    """Persist a building brief back into Elastic."""

    if client._settings.is_demo:
        return SavedBrief(
            address=normalize_address(address),
            stored=True,
            document_id=f"demo-{_slugify(address)}",
        )

    result = await client.call_tool(
        "save_building_brief",
        {"address": address, "risk_score": risk_score, "summary": summary},
    )
    return SavedBrief(
        address=address,
        stored=bool(result.get("stored", True)),
        document_id=str(result.get("document_id", _slugify(address))),
    )


def normalize_address(address: str) -> str:
    """Normalize whitespace and punctuation for the MVP."""

    compact = re.sub(r"\s+", " ", address.strip())
    return compact.replace(" ,", ",")


def _coerce_float(value: Any, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    return float(value)


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _slugify(value: str) -> str:
    lowered = value.lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def _sample_payload(address: str) -> dict[str, Any]:
    normalized = normalize_address(address)
    if "123 orchard" in normalized.lower():
        return {
            "address": "123 Orchard St, New York, NY 10002",
            "memory": {
                "found": True,
                "summary": "Prior brief flagged heat and noise issues in winter and late-night hours.",
                "prior_risk_score": 6.8,
                "prior_flags": ["recurring heat complaints", "late-night noise"],
            },
            "hpd": {
                "open_violations": 5,
                "severe_categories": ["heat/hot water", "pests"],
                "recent_examples": [
                    "Open Class B violation related to inadequate heat.",
                    "Recent pest-related complaint tied to common areas.",
                ],
            },
            "signals": {
                "complaint_count_90d": 18,
                "top_categories": ["noise", "heat", "rodent"],
                "nighttime_noise_share": 0.61,
            },
            "sentiment": {
                "mentions_found": 3,
                "highlights": [
                    "Tenant thread describes thin walls and bar noise after midnight.",
                    "Local post mentions slow landlord response to heat issues.",
                ],
            },
            "baseline": {
                "complaint_index_vs_zip": 1.7,
                "summary": "Complaint density is materially worse than the nearby ZIP baseline.",
            },
        }

    return {
        "address": normalized,
        "memory": {
            "found": False,
            "summary": None,
            "prior_risk_score": None,
            "prior_flags": [],
        },
        "hpd": {
            "open_violations": 2,
            "severe_categories": ["maintenance"],
            "recent_examples": ["Recent maintenance complaint with limited detail."],
        },
        "signals": {
            "complaint_count_90d": 7,
            "top_categories": ["noise", "maintenance"],
            "nighttime_noise_share": 0.34,
        },
        "sentiment": {
            "mentions_found": 1,
            "highlights": ["One weak tenant-signal mention; evidence confidence is limited."],
        },
        "baseline": {
            "complaint_index_vs_zip": 1.1,
            "summary": "This address is slightly above the nearby baseline but not an obvious outlier.",
        },
    }
