#!/usr/bin/env python3
"""Generate before/after traffic against the refund assistant.

Three modes:

  --mode healthy   constant healthy traffic
  --mode bad       constant bad-deploy traffic
  --mode demo      30s healthy → release marker → 30s bad. Used for the
                   judge-facing recording. Each request prints a tagged
                   row so the OTel telemetry in Dynatrace lines up cleanly
                   for the change-analysis window.

Example:
  python scripts/traffic.py --mode demo --requests-per-window 20
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass

import httpx


HEALTHY_MESSAGES = [
    "Can you check refund status for my order?",
    "I'd like to return order ord-10042, what's the status?",
    "My delivery arrived on Tuesday. Is there a return window?",
    "Can you process a refund for order ord-10042?",
]

BAD_MESSAGES = [
    "I'm not sure if I'm eligible for a refund — maybe you can help?",
    "Not sure what to do here, can you help with this refund?",
    "I think maybe this order qualifies? Unclear.",
    "Help, I don't know if I should refund this.",
]


@dataclass
class Phase:
    name: str
    mode: str
    release_id: str
    prompt_version: str
    duration_s: int
    rps: float


def _send(
    client: httpx.Client,
    *,
    phase: Phase,
) -> dict:
    headers = {
        "X-Prompt-Mode": phase.mode,
        "X-Release-Id": phase.release_id,
        "X-Prompt-Version": phase.prompt_version,
    }
    msg_pool = BAD_MESSAGES if phase.mode == "bad" else HEALTHY_MESSAGES
    msg = random.choice(msg_pool)
    response = client.post("/chat", json={"message": msg}, headers=headers)
    response.raise_for_status()
    return response.json()


def _run_phase(client: httpx.Client, phase: Phase) -> None:
    print()
    print("=" * 72)
    print(f"PHASE: {phase.name}")
    print(
        f"  mode={phase.mode}  release={phase.release_id}  "
        f"prompt={phase.prompt_version}  duration={phase.duration_s}s  rps={phase.rps}"
    )
    print("=" * 72)
    end = time.monotonic() + phase.duration_s
    interval = 1.0 / max(phase.rps, 0.1)
    idx = 0
    while time.monotonic() < end:
        try:
            payload = _send(client, phase=phase)
            idx += 1
            tokens = payload.get("input_tokens", 0) + payload.get("output_tokens", 0)
            print(
                f"  [{phase.mode:<7} #{idx:>3}] "
                f"latency={payload['latency_ms']:>4}ms "
                f"tokens={tokens:>4} "
                f"tools={payload['tool_calls']:>2}"
            )
        except Exception as exc:
            print(f"  ERR: {exc}")
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--mode", choices=["healthy", "bad", "demo"], default="demo")
    parser.add_argument("--release-id", default="release-2026-05-26-baseline")
    parser.add_argument("--prompt-version", default="v11")
    parser.add_argument("--requests", type=int, default=15,
                        help="for --mode healthy/bad: total request count")
    parser.add_argument("--rps", type=float, default=2.0,
                        help="requests per second per phase (demo mode)")
    parser.add_argument("--phase-duration", type=int, default=30,
                        help="seconds per phase in demo mode")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=60.0) as client:
        client.get("/healthz").raise_for_status()

        if args.mode in ("healthy", "bad"):
            phase = Phase(
                name=f"static-{args.mode}",
                mode=args.mode,
                release_id=args.release_id,
                prompt_version=args.prompt_version,
                duration_s=int(args.requests / max(args.rps, 0.1)),
                rps=args.rps,
            )
            _run_phase(client, phase)
            return 0

        # --mode demo: warm-up healthy → release marker → bad
        healthy = Phase(
            name="1/3 — baseline (healthy)",
            mode="healthy",
            release_id="release-2026-05-26-baseline",
            prompt_version="v11",
            duration_s=args.phase_duration,
            rps=args.rps,
        )
        bad = Phase(
            name="3/3 — post-release (regression)",
            mode="bad",
            release_id="release-2026-05-26-bad-prompt",
            prompt_version="v12",
            duration_s=args.phase_duration,
            rps=args.rps,
        )

        _run_phase(client, healthy)

        print()
        print("*" * 72)
        print("  RELEASE MARKER  release-2026-05-26-bad-prompt")
        print("  prompt v11 → v12, tool retry caps loosened")
        print("*" * 72)
        time.sleep(3)

        _run_phase(client, bad)

        print()
        print("Done. Trigger the Agent Reliability Guard investigation now:")
        print(
            "  curl -N -X POST $BACKEND_URL/investigate \\\n"
            "    -H 'content-type: application/json' \\\n"
            "    -d '{\"question\": \"Why did refund-assistant regress?\","
            " \"service_name\": \"refund-assistant\","
            " \"release_id\": \"release-2026-05-26-bad-prompt\","
            " \"lookback_minutes\": 60}'"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
