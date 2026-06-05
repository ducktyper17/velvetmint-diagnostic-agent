"""Phoenix tracing setup.

We use ``phoenix.otel.register(auto_instrument=True)`` plus
``openinference-instrumentation-google-adk`` so every ADK call, every Gemini
call, and every MCP tool call is captured as a span without per-callsite
boilerplate. This matches the canonical Arize hackathon reference repo
(https://github.com/Arize-ai/gemini-hackathon).

Both the QA agent and the SUT trace into the same Phoenix project so
cross-agent sessions are inspectable side-by-side in the Phoenix UI.

Auth gotcha (worth memorizing): ``PHOENIX_COLLECTOR_ENDPOINT`` must include
the ``/s/<your-space>`` segment. Bare ``https://app.phoenix.arize.com`` will
401 OTLP traffic. We surface a loud warning if the env var looks wrong so
the developer fixes it before chasing a phantom auth bug.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

from phoenix.otel import register

_log = logging.getLogger(__name__)

_provider: Any | None = None


def setup_tracing() -> Any | None:
    """Register Phoenix tracing once.

    Returns the tracer provider on success, or ``None`` when ``PHOENIX_API_KEY``
    is unset (which is the case in unit tests and during pre-credential
    development). Idempotent: repeated calls return the cached provider.
    """

    global _provider
    if _provider is not None:
        return _provider

    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    if not api_key:
        _log.info("PHOENIX_API_KEY unset; skipping tracer registration.")
        return None

    endpoint = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    if not endpoint:
        # Without a collector URL, phoenix.otel falls back to localhost:4317 and
        # traces never reach Phoenix Cloud — a silent failure during hackathon dev.
        _log.error(
            "PHOENIX_COLLECTOR_ENDPOINT is unset. Copy Hostname from "
            "Phoenix → Settings (must include /s/<your-space>) into .env."
        )
        return None

    if not _looks_like_phoenix_space_endpoint(endpoint):
        _log.warning(
            "PHOENIX_COLLECTOR_ENDPOINT=%r does not look like a Phoenix space "
            "endpoint (expected to contain '/s/<space>'). OTLP will likely 401. "
            "Copy the full Hostname from Phoenix → Settings.",
            endpoint,
        )

    # The Phoenix SDK passes `endpoint` to the OTLP HTTPSpanExporter as the
    # final POST URL, NOT as the base — so we must append /v1/traces ourselves.
    # Without this, exports 405 because Phoenix's /s/<space> root doesn't accept
    # raw OTLP POSTs. The base URL is still what the MCP server gets via
    # --baseUrl, so we only patch the trace export path here.
    traces_endpoint = endpoint.rstrip("/")
    if not traces_endpoint.endswith("/v1/traces"):
        traces_endpoint = f"{traces_endpoint}/v1/traces"

    _provider = register(
        endpoint=traces_endpoint,
        api_key=api_key,
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "self-improving-qa-agent"),
        batch=False,
        auto_instrument=True,
        verbose=False,
    )
    return _provider


def _looks_like_phoenix_space_endpoint(endpoint: str) -> bool:
    """Cheap sanity check; Phoenix Cloud endpoints always carry ``/s/<space>``.

    Self-hosted Phoenix uses arbitrary URLs so we allow anything that isn't the
    bare cloud root.
    """

    try:
        parsed = urlparse(endpoint)
    except ValueError:
        return False
    host = (parsed.netloc or "").lower()
    if host.endswith("phoenix.arize.com"):
        return "/s/" in (parsed.path or "")
    return True
