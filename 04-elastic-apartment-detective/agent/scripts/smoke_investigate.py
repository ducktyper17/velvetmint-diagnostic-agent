"""End-to-end smoke test of the investigation stream (no HTTP server needed).

Runs the agent loop in-process with the current settings and prints each SSE
event. Works offline out of the box (stub planner + demo data); set
STUB_GEMINI_RESPONSES=false and DEMO_MODE=false to exercise the live path.

    source .venv/bin/activate
    python scripts/smoke_investigate.py "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002"
"""

from __future__ import annotations

import asyncio
import sys

from agent.agent_loop import build_listing_context, run_agent_loop
from agent.config import get_settings
from agent.tools import ElasticMCPClient

DEFAULT_URL = "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002"


async def main() -> int:
    listing_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    settings = get_settings()
    context = build_listing_context(
        address=None, listing_url=listing_url, question=None, settings=settings
    )
    print(f"investigating {context.address} (source={context.source})\n")

    mcp = ElasticMCPClient(settings)
    try:
        async for event in run_agent_loop(context=context, settings=settings, mcp=mcp):
            payload = event.payload
            if event.type == "thought":
                print(f"  · {payload.get('text')}")
            elif event.type == "tool_call":
                print(f"  → {payload['name']}({payload.get('args', {})})")
            elif event.type == "tool_result":
                print(f"  ← {payload['name']}: {payload['result']}")
            elif event.type == "final_report":
                print(f"\n★ risk {payload['risk_score']}/10 — {payload['summary']}")
                print(f"  red flags: {payload['top_red_flags']}")
            elif event.type == "error":
                print(f"  ✗ {payload.get('error')}")
                return 1
    finally:
        await mcp.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
