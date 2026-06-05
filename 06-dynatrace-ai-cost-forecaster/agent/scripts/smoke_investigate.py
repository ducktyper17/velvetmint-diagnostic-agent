#!/usr/bin/env python3
"""POST /investigate and print the first few SSE events."""

from __future__ import annotations

import json
import sys

import httpx


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    payload = {
        "question": (
            "Investigate why refund-assistant got slower and more expensive "
            "after release release-2026-05-26-bad-prompt."
        ),
        "service_name": "refund-assistant",
        "release_id": "release-2026-05-26-bad-prompt",
        "lookback_minutes": 180,
    }

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{base_url}/investigate", json=payload) as response:
            response.raise_for_status()
            seen = 0
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    print(line)
                    seen += 1
                if seen >= 12:
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
