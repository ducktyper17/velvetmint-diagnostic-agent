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
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "project-30c02ca7-9a98-43f5-be9")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    print(f"project={project} location={location}")

    client = genai.Client(vertexai=True, project=project, location=location)

    candidate_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash-001",
        "gemini-1.5-pro-002",
    ]

    for model in candidate_models:
        try:
            resp = client.models.generate_content(
                model=model,
                contents="Say the single word ONLINE if you can read this.",
            )
            text = (resp.text or "").strip()
            print(f"OK  {model}: {text!r}")
            return 0
        except Exception as exc:
            print(f"ERR {model}: {type(exc).__name__}: {exc}")
            continue

    print("No working Gemini model found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
