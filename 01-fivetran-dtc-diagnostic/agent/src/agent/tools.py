"""Typed Python wrappers around the Fivetran MCP server's tool surface.

The Fivetran MCP server (https://github.com/fivetran/fivetran-mcp) exposes 161
tools over either stdio or HTTP transports. We use the HTTP transport so the
MCP can run as a separate Cloud Run service and we can authenticate
service-to-service via a bearer token + Cloud Run IAM.

This module exposes a small, opinionated subset of those tools as plain
Python coroutines:

* :func:`setup_connector`     — calls ``create_connection`` (idempotent wrapper)
* :func:`trigger_sync`        — calls ``sync_connection``
* :func:`check_sync_status`   — calls ``get_connection_state``
* :func:`query_synced_data`   — delegates to :mod:`agent.diagnostic_engine`,
                                 NOT the MCP, but is exposed here so the agent
                                 loop has a uniform tool dispatch surface.

Each function returns a Pydantic model so the agent loop can serialize the
result into a tool_result message without ad-hoc dict munging.

The actual MCP HTTP call is stubbed with TODOs — the protocol-level details
(JSON-RPC envelope, SSE streaming for long-running calls) need to be confirmed
against the live MCP server on Day 3 of the build plan.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.config import Settings


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
#
# The Fivetran MCP's `create_connection` accepts the full Fivetran connector
# catalog (~300 sources). We only allow a curated subset so the agent cannot
# hallucinate weird sources, and so we can map each one to its canonical
# BigQuery schema name.

Source = Literal[
    "shopify",
    "klaviyo",
    "meta_ads",
    "google_ads",
    "tiktok_ads",
    "stripe",
    "yotpo",
]


_FIVETRAN_SERVICE_NAMES: dict[Source, str] = {
    # `service` field as Fivetran's REST API expects it. Verify at
    # https://fivetran.com/docs/connectors before build day.
    "shopify": "shopify",
    "klaviyo": "klaviyo",
    "meta_ads": "facebook_ads",
    "google_ads": "google_ads",
    "tiktok_ads": "tiktok_ads",
    "stripe": "stripe",
    "yotpo": "yotpo",
}


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class ConnectorResult(BaseModel):
    """Result of :func:`setup_connector`."""

    source: Source
    connection_id: str
    status: Literal["created", "already_existed"]
    raw: dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Result of :func:`trigger_sync`."""

    connection_id: str
    sync_id: str | None = None
    queued: bool


class SyncStatus(BaseModel):
    """Result of :func:`check_sync_status`."""

    connection_id: str
    state: Literal["pending", "syncing", "complete", "failed"]
    last_sync_at: str | None = None
    rows_synced: int | None = None
    error: str | None = None


class QueryResult(BaseModel):
    """Result of :func:`query_synced_data` — a list of rows from BigQuery."""

    metric: str
    window_days: int
    rows: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# MCP HTTP client
# ---------------------------------------------------------------------------


class FivetranMCPClient:
    """Thin async HTTP client for the Fivetran MCP server.

    The MCP protocol uses JSON-RPC 2.0 over HTTP for tool invocations. Each
    call is `POST /mcp` with `{"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": ..., "arguments": ...}, "id": ...}`. The server returns
    the tool's output in `result.content`.

    We keep one persistent :class:`httpx.AsyncClient` per agent process for
    HTTP/2 connection reuse.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=str(settings.fivetran_mcp_url),
            headers={
                "Authorization": f"Bearer {settings.fivetran_mcp_token.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool by name. Returns the parsed `result.content`.

        Raises :class:`httpx.HTTPStatusError` for non-2xx, and
        :class:`RuntimeError` for JSON-RPC error responses.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 1,  # caller does not use IDs; we serialize calls
        }
        # TODO: confirm exact endpoint path and SSE behavior. The Fivetran MCP
        # may publish a non-standard URL (e.g. "/" or "/rpc"); we'll lock this
        # in on Day 3 when we run it locally.
        resp = await self._client.post("/", json=payload)
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"MCP error calling {name!r}: {body['error']}")
        return body.get("result", {})


# ---------------------------------------------------------------------------
# Tool wrappers
# ---------------------------------------------------------------------------


async def setup_connector(
    client: FivetranMCPClient,
    source: Source,
    *,
    destination_id: str,
    group_id: str,
) -> ConnectorResult:
    """Idempotently set up a Fivetran connector for ``source``.

    The function first calls ``list_connections`` to see if a connection of
    the requested service already exists for this destination. If yes, returns
    its id with ``status="already_existed"`` so the agent treats setup as a
    no-op. Otherwise calls ``create_connection`` (write mode required).

    Args:
        client: live MCP HTTP client.
        source: one of the curated :data:`Source` values.
        destination_id: Fivetran destination id (BigQuery target).
        group_id: Fivetran group id the connection should belong to.
    """
    if source not in _FIVETRAN_SERVICE_NAMES:
        raise ValueError(f"unknown source: {source!r}")
    service = _FIVETRAN_SERVICE_NAMES[source]

    # 1. Check for an existing connection — keeps the agent loop idempotent.
    existing = await client.call_tool("list_connections", {})
    for conn in _iter_connections(existing):
        if conn.get("service") == service and conn.get("group_id") == group_id:
            return ConnectorResult(
                source=source,
                connection_id=conn["id"],
                status="already_existed",
                raw=conn,
            )

    # 2. Create. The exact `config` shape varies per source; the MCP server
    #    encapsulates the required fields. For the demo we rely on the
    #    server's defaults plus an OAuth grant captured during Day 1 setup.
    # TODO: per-source config (auth, sync mode, schema renaming) goes here.
    created = await client.call_tool(
        "create_connection",
        {
            "service": service,
            "group_id": group_id,
            "destination_id": destination_id,
            "run_setup_tests": True,
            "paused": False,
            "config": {},
        },
    )
    connection_id = _extract_connection_id(created)
    return ConnectorResult(
        source=source,
        connection_id=connection_id,
        status="created",
        raw=created,
    )


async def trigger_sync(
    client: FivetranMCPClient,
    connection_id: str,
) -> SyncResult:
    """Kick off a sync on an existing connection."""
    result = await client.call_tool("sync_connection", {"connection_id": connection_id})
    return SyncResult(
        connection_id=connection_id,
        sync_id=result.get("sync_id"),
        queued=True,
    )


async def check_sync_status(
    client: FivetranMCPClient,
    connection_id: str,
) -> SyncStatus:
    """Return the current sync state of a connection."""
    state = await client.call_tool(
        "get_connection_state",
        {"connection_id": connection_id},
    )
    raw_state = state.get("status", "pending")
    # Map Fivetran's status vocabulary onto our four-state enum.
    normalized: Literal["pending", "syncing", "complete", "failed"]
    if raw_state in {"syncing", "running", "in_progress"}:
        normalized = "syncing"
    elif raw_state in {"complete", "success", "succeeded"}:
        normalized = "complete"
    elif raw_state in {"error", "failed", "broken"}:
        normalized = "failed"
    else:
        normalized = "pending"
    return SyncStatus(
        connection_id=connection_id,
        state=normalized,
        last_sync_at=state.get("last_sync_at"),
        rows_synced=state.get("rows_synced"),
        error=state.get("error"),
    )


async def query_synced_data(
    metric: str,
    window_days: int = 30,
    *,
    brand_id: str,
) -> QueryResult:
    """Run a named diagnostic query against the synced BigQuery dataset.

    Delegates to :mod:`agent.diagnostic_engine`. Exposed here so the agent
    loop sees a single uniform tool surface (MCP and analytics look the same
    from the model's perspective).
    """
    # Local import to avoid a circular dependency at module load time.
    from agent.diagnostic_engine import run_named_query

    rows = await run_named_query(metric=metric, window_days=window_days, brand_id=brand_id)
    return QueryResult(metric=metric, window_days=window_days, rows=rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_connections(list_connections_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the shape of the MCP's `list_connections` response.

    The Fivetran MCP wraps results in `{ "content": [ { "type": "text",
    "text": "..." } ] }` for some tools and returns structured payloads for
    others. We tolerate both.
    """
    # TODO: confirm the actual shape on Day 3. Until then, we accept the
    # most likely structures.
    if "items" in list_connections_result:
        return list(list_connections_result["items"])
    if "connections" in list_connections_result:
        return list(list_connections_result["connections"])
    if "content" in list_connections_result:
        # Stringly-typed text content; the agent loop handles parsing.
        return []
    return []


def _extract_connection_id(create_connection_result: dict[str, Any]) -> str:
    """Pull the new connection id out of a `create_connection` response."""
    # TODO: confirm exact field names against live MCP responses on Day 3.
    if "id" in create_connection_result:
        return str(create_connection_result["id"])
    if "connection_id" in create_connection_result:
        return str(create_connection_result["connection_id"])
    raise RuntimeError(
        "create_connection did not return an id; "
        f"got keys={list(create_connection_result)!r}"
    )
