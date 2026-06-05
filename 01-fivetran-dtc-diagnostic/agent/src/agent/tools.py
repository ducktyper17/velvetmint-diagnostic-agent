"""Typed Python wrappers around the Fivetran MCP server's tool surface.

The official Fivetran MCP server is currently stdio-first. For local
development we spawn it as a subprocess and keep one MCP session open for the
life of the app process.

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

The long-term production shape can still move to a dedicated MCP service, but
the local build path should use the official server unmodified so we validate
real tool names and response shapes early.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel, Field

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
# MCP stdio client
# ---------------------------------------------------------------------------


class FivetranMCPClient:
    """Async stdio client for the official Fivetran MCP server."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stdio_cm = None
        self._session: ClientSession | None = None
        self._session_entered = False

    async def initialize(self) -> None:
        """Start the stdio MCP subprocess and initialize a session."""
        if self._session is not None:
            return

        server_path = self._resolve_server_path()
        server_params = StdioServerParameters(
            command="python",
            args=[server_path],
            env={
                "FIVETRAN_API_KEY": self._required_secret(
                    self._settings.fivetran_api_key,
                    "FIVETRAN_API_KEY",
                ),
                "FIVETRAN_API_SECRET": self._required_secret(
                    self._settings.fivetran_api_secret,
                    "FIVETRAN_API_SECRET",
                ),
                "FIVETRAN_ALLOW_WRITES": str(self._settings.fivetran_allow_writes).lower(),
            },
        )
        self._stdio_cm = stdio_client(server_params)
        read_stream, write_stream = await self._stdio_cm.__aenter__()
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        self._session_entered = True
        await self._session.initialize()

    async def aclose(self) -> None:
        if self._session is not None and self._session_entered:
            await self._session.__aexit__(None, None, None)
            self._session_entered = False
        if self._stdio_cm is not None:
            await self._stdio_cm.__aexit__(None, None, None)
        self._session = None
        self._stdio_cm = None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool by name and parse the JSON text response."""
        await self.initialize()
        if self._session is None:
            raise RuntimeError("Fivetran MCP session failed to initialize")

        result = await self._session.call_tool(name, _tool_arguments(name=name, arguments=arguments))
        if getattr(result, "isError", False):
            raise RuntimeError(f"MCP error calling {name!r}: {result.content}")

        text_chunks = [
            part.text
            for part in result.content
            if hasattr(part, "text") and isinstance(part.text, str)
        ]
        if not text_chunks:
            return {}
        body_text = "\n".join(text_chunks)
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"content": body_text}

    def _resolve_server_path(self) -> str:
        """Resolve the local path to the official Fivetran MCP server."""
        if self._settings.fivetran_mcp_server_path:
            return self._settings.fivetran_mcp_server_path
        default_path = Path(__file__).resolve().parents[3] / "fivetran-mcp" / "server.py"
        return str(default_path)

    @staticmethod
    def _required_secret(value, env_name: str) -> str:
        """Fail fast if a required local MCP secret is missing."""
        if value is None:
            raise RuntimeError(f"{env_name} is required for the local Fivetran MCP session")
        return value.get_secret_value()


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
        client: live MCP client.
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
            "run_setup_tests": True,
            "paused": False,
            "destination_schema_names": "FIVETRAN_NAMING",
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
    result = await client.call_tool("sync_connection", {"connection_id": connection_id, "force": False})
    raw = result.get("data", result)
    return SyncResult(
        connection_id=connection_id,
        sync_id=raw.get("sync_id"),
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
    raw = state.get("data", state)
    raw_state = raw.get("sync_state") or raw.get("status") or "pending"
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
        last_sync_at=raw.get("last_sync_at"),
        rows_synced=raw.get("rows_synced"),
        error=raw.get("error"),
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
    data = list_connections_result.get("data", list_connections_result)
    if "items" in data:
        return list(data["items"])
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
    data = create_connection_result.get("data", create_connection_result)
    if "id" in data:
        return str(data["id"])
    if "id" in create_connection_result:
        return str(create_connection_result["id"])
    if "connection_id" in create_connection_result:
        return str(create_connection_result["connection_id"])
    raise RuntimeError(
        "create_connection did not return an id; "
        f"got keys={list(create_connection_result)!r}"
    )


def _tool_arguments(*, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Map simplified wrapper arguments onto the official MCP tool contract."""
    schema_files = {
        "list_connections": "open-api-definitions/connections/list_connections.json",
        "create_connection": "open-api-definitions/connections/create_connection.json",
        "get_connection_state": "open-api-definitions/connections/connection_state.json",
        "sync_connection": "open-api-definitions/connections/sync_connection.json",
    }
    schema_file = schema_files.get(name)
    if schema_file is None:
        raise ValueError(f"Unsupported MCP tool {name!r}")

    if name == "list_connections":
        return {"schema_file": schema_file}
    if name == "create_connection":
        return {"schema_file": schema_file, "request_body": arguments}
    if name == "get_connection_state":
        return {
            "schema_file": schema_file,
            "connection_id": arguments["connection_id"],
        }
    if name == "sync_connection":
        return {
            "schema_file": schema_file,
            "connection_id": arguments["connection_id"],
            "request_body": {"force": bool(arguments.get("force", False))},
        }
    raise ValueError(f"Unsupported MCP tool {name!r}")
