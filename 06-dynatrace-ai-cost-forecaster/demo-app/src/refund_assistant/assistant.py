"""Gemini-backed refund assistant with intentional bad-deploy behavior."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from google import genai

from refund_assistant.telemetry import get_tracer


PromptMode = Literal["healthy", "bad"]


@dataclass(frozen=True)
class ChatSettings:
    """Runtime knobs for one request."""

    prompt_mode: PromptMode
    release_id: str
    prompt_version: str
    model: str
    project: str
    location: str
    stub_gemini: bool


@dataclass
class ChatResult:
    """Response returned to the HTTP layer."""

    reply: str
    tool_calls: int
    input_tokens: int
    output_tokens: int
    latency_ms: int


async def run_chat(*, message: str, settings: ChatSettings) -> ChatResult:
    """Handle one user message with traced tool simulation."""

    tracer = get_tracer()
    started = time.perf_counter()
    tool_calls = 0
    input_tokens = 0
    output_tokens = 0

    with tracer.start_as_current_span("chat") as root:
        root.set_attribute("release_id", settings.release_id)
        root.set_attribute("prompt_version", settings.prompt_version)
        root.set_attribute("prompt_mode", settings.prompt_mode)

        order = _lookup_order(message)
        tool_calls += 1
        with tracer.start_as_current_span("tool.refund_check") as tool_span:
            tool_span.set_attribute("tool.name", "refund_check")
            refund = await _refund_check(
                order_id=order["order_id"],
                ambiguous=_is_ambiguous(message),
                settings=settings,
            )
            tool_span.set_attribute("tool.status", refund["status"])
            tool_calls += refund.get("extra_calls", 0)

        if settings.stub_gemini:
            reply = _stub_reply(message=message, refund=refund, settings=settings)
            input_tokens = 120
            output_tokens = 80
        else:
            gemini_text, usage = await _call_gemini(message=message, refund=refund, settings=settings)
            reply = gemini_text
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        root.set_attribute("llm.tokens.input", input_tokens)
        root.set_attribute("llm.tokens.output", output_tokens)
        root.set_attribute("llm.tokens.total", input_tokens + output_tokens)

    latency_ms = int((time.perf_counter() - started) * 1000)
    return ChatResult(
        reply=reply,
        tool_calls=tool_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )


def load_settings_from_env() -> ChatSettings:
    """Build settings from environment variables."""

    mode = os.getenv("PROMPT_MODE", "healthy").strip().lower()
    prompt_mode: PromptMode = "bad" if mode == "bad" else "healthy"
    stub_gemini = os.getenv("STUB_GEMINI", "false").lower() == "true"
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project and not stub_gemini:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT or STUB_GEMINI=true for offline runs.")
    return ChatSettings(
        prompt_mode=prompt_mode,
        release_id=os.getenv("RELEASE_ID", "release-baseline"),
        prompt_version=os.getenv("PROMPT_VERSION", "v11"),
        model=os.getenv("VERTEX_MODEL", "gemini-2.5-flash"),
        project=project or "offline-demo",
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        stub_gemini=stub_gemini,
    )


def _lookup_order(message: str) -> dict[str, str]:
    """Pretend to call an order lookup tool."""

    order_id = "ord-10042" if "order" in message.lower() else "ord-unknown"
    return {"order_id": order_id, "status": "shipped"}


async def _refund_check(
    *,
    order_id: str,
    ambiguous: bool,
    settings: ChatSettings,
) -> dict[str, Any]:
    """Simulate refund eligibility checks with optional retry storm."""

    tracer = get_tracer()
    retries = 1
    if settings.prompt_mode == "bad" and ambiguous:
        retries = 3

    status = "ok"
    for attempt in range(retries):
        with tracer.start_as_current_span("tool.refund_check.retry") as span:
            span.set_attribute("tool.name", "refund_check")
            span.set_attribute("attempt", attempt + 1)
            await asyncio.sleep(0.15 if settings.prompt_mode == "bad" else 0.03)
            if settings.prompt_mode == "bad" and ambiguous and attempt < retries - 1:
                status = "retry"
                span.set_attribute("tool.status", status)
            else:
                status = "ok" if order_id != "ord-unknown" else "error"
                span.set_attribute("tool.status", status)

    return {
        "order_id": order_id,
        "eligible": order_id != "ord-unknown",
        "status": status,
        "extra_calls": max(0, retries - 1),
    }


async def _call_gemini(
    *,
    message: str,
    refund: dict[str, Any],
    settings: ChatSettings,
) -> tuple[str, dict[str, int]]:
    """Call Gemini on Vertex AI."""

    client = _get_genai_client(project=settings.project, location=settings.location)
    prompt = (
        "You are a concise customer-support agent for refunds. "
        f"Order check: {refund}. User message: {message}"
    )

    def _generate() -> Any:
        return client.models.generate_content(model=settings.model, contents=prompt)

    response = await asyncio.to_thread(_generate)
    usage_metadata = getattr(response, "usage_metadata", None)
    usage = {
        "input_tokens": int(getattr(usage_metadata, "prompt_token_count", 0) or 0),
        "output_tokens": int(getattr(usage_metadata, "candidates_token_count", 0) or 0),
    }
    return (response.text or "").strip(), usage


def _stub_reply(*, message: str, refund: dict[str, Any], settings: ChatSettings) -> str:
    """Deterministic reply for offline demos."""

    eligible = "eligible" if refund.get("eligible") else "not eligible"
    return (
        f"[{settings.prompt_version}/{settings.release_id}] "
        f"Refund is {eligible} for your request: {message[:120]}"
    )


def _is_ambiguous(message: str) -> bool:
    """Heuristic for messages that trigger the bad-deploy retry loop."""

    lowered = message.lower()
    return any(word in lowered for word in ("maybe", "not sure", "unclear", "help"))


@lru_cache(maxsize=4)
def _get_genai_client(*, project: str, location: str) -> genai.Client:
    return genai.Client(vertexai=True, project=project, location=location)
