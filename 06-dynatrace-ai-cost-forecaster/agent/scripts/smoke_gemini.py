"""Quick Gemini smoke test using ADC.

Run from the agent venv with the project set:

    source .venv/bin/activate
    python scripts/smoke_gemini.py
"""

from __future__ import annotations

import os
import sys

from google import genai


def main() -> int:
    """Try a few Google-hosted Gemini models and print the first success."""

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        print("Set GOOGLE_CLOUD_PROJECT before running this smoke test.")
        return 1

    print(f"project={project} location={location}")

    client = genai.Client(vertexai=True, project=project, location=location)

    preferred = os.environ.get("VERTEX_MODEL", "gemini-2.5-pro")
    candidate_models = [
        preferred,
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash-001",
    ]

    seen: set[str] = set()
    for model in candidate_models:
        if model in seen:
            continue
        seen.add(model)
        try:
            response = client.models.generate_content(
                model=model,
                contents="Reply with the single word ONLINE.",
            )
            print(f"OK  {model}: {(response.text or '').strip()!r}")
            return 0
        except Exception as exc:
            print(f"ERR {model}: {type(exc).__name__}: {exc}")

    print("No working Gemini model found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
