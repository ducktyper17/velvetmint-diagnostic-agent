"""Typed wrappers around the Dynatrace MCP server tool surface."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.config import Settings

log = logging.getLogger(__name__)


class RuntimeSignalsResult(BaseModel):
    """Result of querying runtime telemetry."""

    service_name: str
    release_id: str | None
    lookback_minutes: int
    dql: str
    summary: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AnalyzerResult(BaseModel):
    """Result of a Davis analyzer call."""

    analyzer_name: str
    verdict: str
    evidence: str
    raw: dict[str, Any] = Field(default_factory=dict)


class NotebookResult(BaseModel):
    """Result of creating a Dynatrace notebook."""

    title: str
    notebook_id: str
    url: str
    status: str
    raw: dict[str, Any] = Field(default_factory=dict)


class NotificationResult(BaseModel):
    """Result of notifying the service owner."""

    channel: str
    delivery: str
    message_preview: str
    raw: dict[str, Any] = Field(default_factory=dict)


class DynatraceMCPClient:
    """Thin async HTTP client for the Dynatrace MCP endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._endpoint = str(settings.dynatrace_mcp_url)
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {settings.dynatrace_mcp_token.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
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
        """Invoke a Dynatrace MCP tool by name via JSON-RPC over HTTP."""

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 1,
        }
        response = await self._client.post(self._endpoint, json=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"MCP error calling {name!r}: {body['error']}")
        result = _normalize_mcp_result(body.get("result", {}))
        # The platform MCP gateway reports tool-level failures (bad args, missing
        # scope, unknown tool) inside result.content with isError=true rather than
        # as a JSON-RPC error. Surface those so _call_tool_variants can fall back.
        if result.get("isError"):
            raise RuntimeError(
                f"MCP tool {name!r} returned error: {result.get('text') or result}"
            )
        return result


async def query_runtime_signals(
    client: DynatraceMCPClient,
    *,
    service_name: str,
    lookback_minutes: int,
    release_id: str | None,
) -> RuntimeSignalsResult:
    """Query the core runtime signals used in the investigation."""

    dql = _build_signal_query(service_name=service_name, lookback_minutes=lookback_minutes)

    if client._settings.stub_dynatrace_tools:
        return _stub_runtime_signals(
            service_name=service_name,
            release_id=release_id,
            lookback_minutes=lookback_minutes,
            dql=dql,
        )

    raw = await _call_tool_variants(
        client,
        [
            # Live platform MCP gateway tool (verified on tenant rzw85677).
            ("execute-dql", {"dqlQueryString": dql}),
            # Legacy / alternate builds of the standalone Dynatrace MCP server.
            ("execute_dql", {"query": dql, "dtClientContext": "agent-reliability-guard"}),
            ("execute_dql", {"dql": dql, "dtClientContext": "agent-reliability-guard"}),
            ("execute_dql", {"statement": dql}),
            ("execute_dql", {"query": dql}),
        ],
    )
    rows = _extract_rows(raw)
    summary = _summarize_runtime_signals(rows, release_id=release_id)
    return RuntimeSignalsResult(
        service_name=service_name,
        release_id=release_id,
        lookback_minutes=lookback_minutes,
        dql=dql,
        summary=summary,
        rows=rows,
        raw=raw,
    )


async def run_change_analysis(
    client: DynatraceMCPClient,
    *,
    service_name: str,
    lookback_minutes: int,
    release_id: str | None,
) -> AnalyzerResult:
    """Run the Davis analyzer used for changepoint detection."""

    if client._settings.stub_dynatrace_tools:
        return _stub_change_analysis()

    analyzer_name = client._settings.dynatrace_change_analyzer_name
    timeseries = _build_timeseries_query(
        service_name=service_name, lookback_minutes=lookback_minutes, metric="p95_latency_ms"
    )
    general = _general_parameters(lookback_minutes)
    raw = await _call_tool_variants(
        client,
        [
            # Live platform MCP gateway: dedicated changepoint analyzer.
            (
                "timeseries-novelty-detection",
                {"generalParameters": general, "timeSeriesData": timeseries},
            ),
            (analyzer_name, {"generalParameters": general, "timeSeriesData": timeseries}),
            # Legacy generic Davis analyzer surface.
            ("execute_davis_analyzer", {"name": analyzer_name, "timeframe": f"{lookback_minutes}m", "input": timeseries}),
        ],
    )
    return AnalyzerResult(
        analyzer_name=analyzer_name,
        verdict=_pick_first_string(raw, ["verdict", "summary", "message", "result"])
        or "Davis analyzer completed.",
        evidence=_pick_first_string(raw, ["evidence", "details", "description", "reason"])
        or _truncate_json(raw),
        raw=raw,
    )


async def forecast_blast_radius(
    client: DynatraceMCPClient,
    *,
    service_name: str,
    lookback_minutes: int,
    release_id: str | None,
) -> AnalyzerResult:
    """Forecast the operational blast radius if the regression remains live."""

    if client._settings.stub_dynatrace_tools:
        return _stub_forecast()

    analyzer_name = client._settings.dynatrace_forecast_analyzer_name
    timeseries = _build_timeseries_query(
        service_name=service_name, lookback_minutes=lookback_minutes, metric="tokens_per_request"
    )
    general = _general_parameters(lookback_minutes)
    raw = await _call_tool_variants(
        client,
        [
            # Live platform MCP gateway: dedicated forecasting analyzer.
            (
                "timeseries-forecast",
                {"generalParameters": general, "query": timeseries, "forecastHorizon": 100},
            ),
            (analyzer_name, {"generalParameters": general, "query": timeseries, "forecastHorizon": 100}),
            # Legacy generic Davis analyzer surface.
            ("execute_davis_analyzer", {"name": analyzer_name, "timeframe": f"{lookback_minutes}m", "input": timeseries}),
        ],
    )
    return AnalyzerResult(
        analyzer_name=analyzer_name,
        verdict=_pick_first_string(raw, ["verdict", "summary", "message", "result"])
        or "Forecast completed.",
        evidence=_pick_first_string(raw, ["evidence", "details", "description", "reason"])
        or _truncate_json(raw),
        raw=raw,
    )


async def draft_notebook(
    client: DynatraceMCPClient,
    *,
    title: str,
    summary: str,
    evidence: dict[str, Any] | None = None,
) -> NotebookResult:
    """Create a Dynatrace notebook for the current investigation.

    When ``evidence`` (the accumulated runtime-signal, changepoint, and forecast
    results from earlier in the loop) is supplied, the notebook is built as a
    full multi-section investigation artifact rather than a single blurb.
    """

    if client._settings.stub_dynatrace_tools:
        return _stub_notebook(client, title)

    sections = _notebook_sections(title=title, summary=summary, evidence=evidence or {})

    # The platform MCP gateway exposes read-only document tools (find-documents)
    # but no notebook-creation tool. Create a REAL Dynatrace notebook directly via
    # the Documents REST API (token scope document:documents:write), then fall back
    # to the legacy MCP tool name, then to a deterministic stub. This produces a
    # genuine, shareable artifact in the tenant — the thing an operator opens.
    try:
        raw = await _create_notebook_document(client, title=title, sections=sections)
        notebook_id = str(raw.get("id") or "unknown-notebook")
        return NotebookResult(
            title=str(raw.get("name") or title),
            notebook_id=notebook_id,
            url=_notebook_url(client, notebook_id),
            status="created",
            raw=raw,
        )
    except Exception as exc:
        log.info("draft_notebook.documents_api_failed", extra={"error": str(exc)[:200]})

    try:
        raw = await _call_tool_variants(
            client,
            [
                ("create_dynatrace_notebook", {"title": title, "content": summary}),
                ("create_dynatrace_notebook", {"name": title, "markdown": summary}),
            ],
        )
    except Exception:
        log.info("draft_notebook.no_mcp_tool_falling_back_to_stub")
        return _stub_notebook(client, title)

    notebook_id = str(raw.get("id") or raw.get("notebook_id") or "unknown-notebook")
    url = str(raw.get("url") or raw.get("link") or _notebook_fallback_url(client, title))
    return NotebookResult(
        title=str(raw.get("title") or raw.get("name") or title),
        notebook_id=notebook_id,
        url=url,
        status=str(raw.get("status") or "created"),
        raw=raw,
    )


async def notify_owner(
    client: DynatraceMCPClient,
    *,
    channel: str,
    summary: str,
) -> NotificationResult:
    """Send an operator-facing notification."""

    if client._settings.stub_dynatrace_tools:
        return _stub_notification(channel=channel, summary=summary)

    # Neither a Slack tool nor a workflow-notification tool is exposed on the
    # platform MCP gateway. Try the legacy standalone-server tool names, then
    # fall back to a deterministic queued notification. A real alert would use
    # the Workflows REST API directly, outside MCP.
    try:
        raw = await _call_tool_variants(
            client,
            [
                ("send_slack_message", {"channel": channel, "message": summary}),
                ("send_slack_message", {"channelName": channel, "message": summary}),
                (
                    "create_workflow_for_notification",
                    {"title": "Agent Reliability Guard alert", "channel": channel, "message": summary},
                ),
            ],
        )
        delivery = str(raw.get("status") or raw.get("delivery") or "queued")
    except Exception:
        log.info("notify_owner.no_mcp_tool_falling_back_to_stub")
        return _stub_notification(channel=channel, summary=summary)

    return NotificationResult(
        channel=channel,
        delivery=delivery,
        message_preview=summary[:180],
        raw=raw,
    )


async def _call_tool_variants(
    client: DynatraceMCPClient,
    variants: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Try several (tool_name, arguments) pairs before failing.

    Tool names and argument shapes differ between the platform-hosted MCP
    gateway and the standalone Dynatrace MCP server. We try the verified
    live-gateway variant first, then legacy shapes, and surface the first
    success.
    """

    errors: list[str] = []
    for name, arguments in variants:
        try:
            return await client.call_tool(name, arguments)
        except Exception as exc:
            errors.append(f"{name}{list(arguments)}: {exc}")
    raise RuntimeError(f"All tool variants failed: {' | '.join(errors)}")


def _general_parameters(lookback_minutes: int) -> dict[str, Any]:
    """Build the generalParameters.timeframe payload the analyzers expect."""

    return {"timeframe": {"startTime": f"now-{lookback_minutes}m", "endTime": "now"}}


def _build_timeseries_query(*, service_name: str, lookback_minutes: int, metric: str) -> str:
    """Return a single-series DQL query for a Davis timeseries analyzer.

    The changepoint and forecasting analyzers take one timeseries (via DQL),
    not the tabular runtime-signals query. p95 latency drives changepoint
    detection; token burn drives the cost forecast.
    """

    measure = "avg(llm.tokens.total)" if metric == "tokens_per_request" else "percentile(duration, 95)"
    return (
        f"timeseries value = {measure}, interval: 5m, from: now-{lookback_minutes}m, "
        f'filter: {{ service.name == "{service_name}" }}'
    )


def _normalize_mcp_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize common MCP result shapes into a dict."""

    normalized: dict[str, Any] = {}
    if isinstance(result, dict):
        normalized.update(result)

    structured = normalized.get("structuredContent")
    if isinstance(structured, dict):
        normalized = {**structured, **normalized}
    elif structured is not None:
        normalized["structuredContent"] = structured

    content = normalized.get("content")
    if isinstance(content, list):
        text_chunks = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if text_chunks:
            text = "\n".join(chunk for chunk in text_chunks if chunk).strip()
            normalized.setdefault("text", text)
            if text:
                parsed = _try_parse_json(text)
                if isinstance(parsed, dict):
                    normalized = {**parsed, **normalized}
                elif isinstance(parsed, list):
                    normalized.setdefault("rows", parsed)
    return normalized


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    """Best-effort extraction of tabular result rows from a tool response."""

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("rows", "records", "items", "data", "values", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for value in payload.values():
        if isinstance(value, dict):
            nested_rows = _extract_rows(value)
            if nested_rows:
                return nested_rows
    return []


def _summarize_runtime_signals(rows: list[dict[str, Any]], *, release_id: str | None) -> str:
    """Create a human-readable one-line summary from the DQL result rows."""

    if len(rows) >= 2:
        baseline = rows[0]
        current = rows[-1]
        baseline_latency = baseline.get("p95_latency_ms")
        current_latency = current.get("p95_latency_ms")
        baseline_tokens = baseline.get("tokens_per_request")
        current_tokens = current.get("tokens_per_request")
        if all(isinstance(value, (int, float)) for value in (
            baseline_latency,
            current_latency,
            baseline_tokens,
            current_tokens,
        )):
            latency_ratio = float(current_latency) / max(float(baseline_latency), 1.0)
            token_ratio = float(current_tokens) / max(float(baseline_tokens), 1.0)
            release_clause = f" after {release_id}" if release_id else ""
            return (
                f"Runtime signals degraded{release_clause}: p95 latency is up {latency_ratio:.1f}x "
                f"and tokens per request are up {token_ratio:.1f}x."
            )

    if rows:
        return f"Retrieved {len(rows)} runtime signal rows from Dynatrace."
    return "Dynatrace query completed, but no structured rows were returned."


def _pick_first_string(payload: dict[str, Any], keys: list[str]) -> str | None:
    """Return the first string-ish value found under the provided keys."""

    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return None


def _truncate_json(payload: dict[str, Any], limit: int = 220) -> str:
    """Return a compact JSON preview for raw payloads."""

    return json.dumps(payload, sort_keys=True)[:limit]


def _try_parse_json(text: str) -> dict[str, Any] | list[Any] | None:
    """Parse JSON if the text looks like JSON; otherwise return None."""

    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None


def _notebook_fallback_url(client: DynatraceMCPClient, title: str) -> str:
    """Build a reasonable notebook URL when the tool response omits one."""

    slug = title.lower().replace(" ", "-")[:48]
    return f"{client._settings.dynatrace_environment_url}/ui/document/v0/#notebook/{slug}"


def _notebook_url(client: DynatraceMCPClient, notebook_id: str) -> str:
    """Build the Notebooks app URL for a created document id."""

    base = str(client._settings.dynatrace_environment_url).rstrip("/")
    return f"{base}/ui/apps/dynatrace.notebooks/notebook/{notebook_id}"


def _notebook_sections(
    *, title: str, summary: str, evidence: dict[str, Any]
) -> list[str]:
    """Build the markdown tiles for an investigation notebook from real evidence.

    ``evidence`` is keyed by tool name (query_runtime_signals, run_change_analysis,
    forecast_blast_radius) with each tool's result dict. Missing pieces are simply
    omitted, so the notebook degrades gracefully if a step was skipped.
    """

    signals = evidence.get("query_runtime_signals") or {}
    change = evidence.get("run_change_analysis") or {}
    forecast = evidence.get("forecast_blast_radius") or {}

    service = signals.get("service_name") or "the service"
    release = signals.get("release_id") or "the latest release"

    sections: list[str] = [
        f"# {title}\n\n"
        f"**Service:** `{service}`  **Release:** `{release}`\n\n"
        "Autonomous investigation by the Agent Reliability Guard: runtime signals "
        "from Dynatrace, Davis changepoint + forecast, and a recommended fix."
    ]
    if summary:
        sections.append(f"## Summary\n\n> {summary}")

    rows = signals.get("rows") or []
    if rows:
        table = _markdown_table(rows)
        dql = signals.get("dql")
        block = "## Runtime signals\n\n"
        if dql:
            block += f"```\n{dql}\n```\n\n"
        block += table
        sections.append(block)

    if change.get("verdict"):
        block = f"## Changepoint (Davis)\n\n**Analyzer:** `{change.get('analyzer_name', 'changepoint')}`\n\n{change['verdict']}"
        if change.get("evidence"):
            block += f"\n\n{change['evidence']}"
        sections.append(block)

    if forecast.get("verdict"):
        block = f"## Forecast — blast radius if unfixed (Davis)\n\n**Analyzer:** `{forecast.get('analyzer_name', 'forecast')}`\n\n{forecast['verdict']}"
        if forecast.get("evidence"):
            block += f"\n\n{forecast['evidence']}"
        sections.append(block)

    return sections


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    """Render a list of flat dict rows as a GitHub-flavored markdown table."""

    cols: list[str] = []
    for row in rows:
        for key in row:
            if key not in cols:
                cols.append(key)
    if not cols:
        return ""
    header = "| " + " | ".join(cols) + " |"
    divider = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join(
        "| " + " | ".join(str(row.get(c, "")) for c in cols) + " |" for row in rows
    )
    return f"{header}\n{divider}\n{body}"


async def _create_notebook_document(
    client: DynatraceMCPClient, *, title: str, sections: list[str]
) -> dict[str, Any]:
    """Create a real Dynatrace notebook via the Documents REST API.

    The platform MCP gateway has no notebook-write tool, so this posts directly
    to /platform/document/v1/documents (multipart) using the same platform token,
    which carries document:documents:write. Verified against tenant rzw85677.
    Each entry in ``sections`` becomes a markdown tile in the notebook.
    """

    base = str(client._settings.dynatrace_environment_url).rstrip("/")
    url = f"{base}/platform/document/v1/documents"
    content = {
        "version": "7",
        "defaultTimeframe": {"from": "now-3h", "to": "now"},
        "sections": [
            {"id": f"s{i}", "type": "markdown", "markdown": md}
            for i, md in enumerate(sections)
        ],
    }
    token = client._settings.dynatrace_mcp_token.get_secret_value()
    files = {
        "name": (None, title),
        "type": (None, "notebook"),
        "content": ("content.json", json.dumps(content), "application/json"),
    }
    # Use a dedicated client: the shared MCP client pins Content-Type: application/json,
    # which would clobber the multipart boundary httpx sets for a file upload.
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as doc:
        resp = await doc.post(
            url, headers={"Authorization": f"Bearer {token}"}, files=files
        )
        resp.raise_for_status()
        return resp.json()


def _stub_runtime_signals(
    *,
    service_name: str,
    release_id: str | None,
    lookback_minutes: int,
    dql: str,
) -> RuntimeSignalsResult:
    """Return a deterministic runtime-signals payload for tests and offline work."""

    rows = [
        {
            "bucket": "baseline",
            "p95_latency_ms": 1800,
            "tokens_per_request": 920,
            "tool_error_rate": 0.01,
        },
        {
            "bucket": "current",
            "p95_latency_ms": 3810,
            "tokens_per_request": 3510,
            "tool_error_rate": 0.14,
        },
    ]
    return RuntimeSignalsResult(
        service_name=service_name,
        release_id=release_id,
        lookback_minutes=lookback_minutes,
        dql=dql,
        summary=_summarize_runtime_signals(rows, release_id=release_id),
        rows=rows,
        raw={"stub": True},
    )


def _stub_change_analysis() -> AnalyzerResult:
    """Return a deterministic changepoint result."""

    return AnalyzerResult(
        analyzer_name="Changepoint Agent",
        verdict="Regression begins within 5 minutes of the provided release marker.",
        evidence="Latency, tool retries, and token burn all shift at the same boundary.",
        raw={"confidence": "high", "stub": True},
    )


def _stub_forecast() -> AnalyzerResult:
    """Return a deterministic forecast result."""

    return AnalyzerResult(
        analyzer_name="Forecasting Agent",
        verdict="If unchanged for 7 days, projected added token spend is about $3.4k.",
        evidence="Current request rate and token inflation were extrapolated over one week.",
        raw={"projected_cost_usd": 3480, "window_days": 7, "stub": True},
    )


def _stub_notebook(client: DynatraceMCPClient, title: str) -> NotebookResult:
    """Return a deterministic notebook creation result."""

    return NotebookResult(
        title=title,
        notebook_id="draft-notebook-001",
        url=_notebook_fallback_url(client, title),
        status="created",
        raw={"stub": True},
    )


def _stub_notification(*, channel: str, summary: str) -> NotificationResult:
    """Return a deterministic notification result."""

    return NotificationResult(
        channel=channel,
        delivery="queued",
        message_preview=summary[:180],
        raw={"stub": True},
    )


def _build_signal_query(*, service_name: str, lookback_minutes: int) -> str:
    """Return a starter DQL query for the service's runtime signals."""

    return (
        "fetch spans\n"
        f'| filter service.name == "{service_name}"\n'
        f"| filter timestamp >= now() - {lookback_minutes}m\n"
        "| summarize "
        "p95_latency_ms = percentile(duration, 95), "
        "tokens_per_request = avg(llm.tokens.total), "
        "tool_error_rate = avg(if(tool.status == \"error\", 1, 0)) "
        "by: { bin(timestamp, 5m), release_id }\n"
        "| sort timestamp asc"
    )
