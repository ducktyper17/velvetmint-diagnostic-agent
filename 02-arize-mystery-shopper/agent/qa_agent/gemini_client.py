"""Thin Gemini client wrapper shared by the cluster, mutate, and judge tools.

Why this module exists:

- We need to call Gemini from inside three tool implementations. Each was
  reinventing client setup, JSON parsing, and retry. Centralizing here means
  one place to change when Vertex / API-key behavior shifts.
- The hackathon rules forbid any non-Google model. Pinning the call site here
  makes "we never call OpenAI / Anthropic" auditable in one file.
- OpenInference's google-genai instrumentor traces every call from this
  module automatically, so we get Phoenix spans without per-call setup.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types

_log = logging.getLogger(__name__)

_client: genai.Client | None = None

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def get_client() -> genai.Client:
    """Return a singleton google-genai client.

    Honors GOOGLE_GENAI_USE_VERTEXAI=1 (preferred for the hackathon — uses
    Application Default Credentials so we never check a key into the repo).
    Falls back to GOOGLE_API_KEY when Vertex isn't available.
    """

    global _client
    if _client is not None:
        return _client

    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip() in {"1", "true", "True"}
    if use_vertex:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        if not project:
            raise RuntimeError(
                "GOOGLE_GENAI_USE_VERTEXAI=1 but GOOGLE_CLOUD_PROJECT is unset."
            )
        _client = genai.Client(vertexai=True, project=project, location=location)
    else:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set GOOGLE_GENAI_USE_VERTEXAI=1 (recommended) or GOOGLE_API_KEY."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_json(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.2,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Call Gemini, demand a JSON object back, parse it.

    The JSON mime type forces the model to emit a single JSON value. We
    still defensively strip ```json fences in case the model wraps the
    object anyway (older Gemini revisions sometimes do).
    """

    client = get_client()
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
    )

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()
            return _parse_json(text)
        except Exception as exc:  # noqa: BLE001 — broad on purpose, we retry
            last_err = exc
            _log.warning("generate_json attempt %d failed: %r", attempt + 1, exc)
    raise RuntimeError(f"generate_json exhausted retries: {last_err!r}")


def generate_text(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.5,
    system_instruction: str | None = None,
) -> str:
    """Plain-text Gemini call. Used by the driver agent (single-turn)."""

    client = get_client()
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()


def _parse_json(text: str) -> dict[str, Any]:
    """Defensive JSON parser. Strips fences then tries plain json.loads."""

    text = text.strip()
    if not text:
        raise ValueError("model returned empty string")

    # Try direct parse first — it's what response_mime_type=application/json
    # should give us.
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(text)
        if not m:
            raise ValueError(f"could not find JSON object in: {text[:200]!r}") from None
        parsed = json.loads(m.group(1))

    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
    return parsed


__all__ = ["get_client", "generate_json", "generate_text"]
