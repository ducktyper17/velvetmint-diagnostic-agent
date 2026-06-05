"""Shared Google Gen AI SDK helpers for the Doctor's Note Decoder.

Why this module exists:
    We want one place that owns:
      1. Google-hosted Gemini / embedding client initialization.
      2. Environment-derived model names and dimensions.
      3. The thin wrapper around Vertex embeddings used by both seed-time
         document indexing and request-time retrieval.

    This keeps the rest of the codebase free of SDK boilerplate and makes
    the hackathon rule compliance obvious: Google models on the model side,
    MongoDB Atlas on the retrieval side.
"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Literal

from google import genai
from google.genai import types


EmbeddingTaskType = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


def get_project() -> str:
    """Return the configured GCP project or fail loudly."""

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI access.")
    return project


def get_location() -> str:
    """Return the configured Vertex location."""

    return os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip() or "us-central1"


def get_gemini_model() -> str:
    """Return the configured Gemini model name."""

    return os.getenv("GEMINI_MODEL", "gemini-2.5-pro").strip() or "gemini-2.5-pro"


def get_embedding_model() -> str:
    """Return the configured embedding model name."""

    return os.getenv("VERTEX_EMBEDDING_MODEL", "gemini-embedding-001").strip() or "gemini-embedding-001"


def get_embedding_dimensions() -> int:
    """Return the configured embedding dimensionality."""

    value = os.getenv("VERTEX_EMBEDDING_DIM", "3072").strip() or "3072"
    return int(value)


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Return a cached Google Gen AI client configured for Vertex AI."""

    return genai.Client(vertexai=True, project=get_project(), location=get_location())


def embed_text(
    text: str,
    *,
    task_type: EmbeddingTaskType,
    title: str | None = None,
) -> list[float]:
    """Generate one embedding vector using a Google-hosted Vertex model."""

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Cannot embed empty text.")

    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=get_embedding_dimensions(),
        title=title,
    )
    response = get_client().models.embed_content(
        model=get_embedding_model(),
        contents=cleaned,
        config=config,
    )
    return list(response.embeddings[0].values)


async def embed_text_async(
    text: str,
    *,
    task_type: EmbeddingTaskType,
    title: str | None = None,
) -> list[float]:
    """Async wrapper around :func:`embed_text` for request handlers."""

    return await asyncio.to_thread(
        embed_text,
        text,
        task_type=task_type,
        title=title,
    )
