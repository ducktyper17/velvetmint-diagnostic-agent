"""Vertex AI / Gemini helpers for Blast Radius."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from google import genai

from agent.config import Settings


@lru_cache(maxsize=4)
def get_genai_client(*, project: str, location: str) -> genai.Client:
    """Return a cached Google Gen AI client configured for Vertex AI."""

    return genai.Client(vertexai=True, project=project, location=location)


async def generate_text(*, settings: Settings, prompt: str) -> str:
    """Generate plain text from Gemini on a worker thread."""

    client = get_genai_client(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )

    def _call() -> str:
        response = client.models.generate_content(
            model=settings.vertex_model,
            contents=prompt,
        )
        return (response.text or "").strip()

    return await asyncio.to_thread(_call)
