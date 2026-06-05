"""OpenTelemetry bootstrap for Dynatrace export."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


_initialized = False


def setup_telemetry() -> None:
    """Configure OTLP export when endpoint env vars are present."""

    global _initialized
    if _initialized:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        _initialized = True
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "refund-assistant")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    headers = _parse_otlp_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers or None)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer() -> Tracer:
    """Return the app tracer."""

    setup_telemetry()
    return trace.get_tracer("refund-assistant")


def _parse_otlp_headers(raw: str) -> dict[str, str] | None:
    """Parse `Key=Value` pairs separated by commas."""

    if not raw.strip():
        return None
    headers: dict[str, str] = {}
    for part in raw.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers or None
