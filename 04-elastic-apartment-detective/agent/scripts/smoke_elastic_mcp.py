"""Smoke test the live Elastic Agent Builder MCP tools.

Lists the tools the MCP endpoint exposes, then calls each apartment-detective
tool for the demo address and prints the normalized result. Requires
ELASTIC_MCP_URL + ELASTIC_MCP_API_KEY and DEMO_MODE=false.

    source .venv/bin/activate
    python scripts/smoke_elastic_mcp.py
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from agent.config import get_settings
from agent.tools import (
    ElasticMCPClient,
    compare_to_neighborhood_baseline,
    get_311_signals,
    get_hpd_violations,
    search_building_memory,
    search_tenant_sentiment,
)

DEMO_ADDRESS = "123 Orchard St, New York, NY 10002"


async def _list_tools(settings) -> None:
    payload = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            str(settings.elastic_mcp_url),
            headers={
                "Authorization": f"ApiKey {settings.elastic_mcp_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        tools = resp.json().get("result", {}).get("tools", [])
        print(f"MCP exposes {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.get('name')}")


async def main() -> int:
    settings = get_settings()
    if settings.is_demo:
        print("DEMO_MODE is on — set DEMO_MODE=false to hit the live MCP endpoint.")
        return 1

    await _list_tools(settings)
    mcp = ElasticMCPClient(settings)
    try:
        print("\nmemory   :", (await search_building_memory(mcp, address=DEMO_ADDRESS)).model_dump())
        print("hpd      :", (await get_hpd_violations(mcp, address=DEMO_ADDRESS)).model_dump())
        print("311      :", (await get_311_signals(mcp, address=DEMO_ADDRESS)).model_dump())
        print("sentiment:", (await search_tenant_sentiment(mcp, address=DEMO_ADDRESS)).model_dump())
        print("baseline :", (await compare_to_neighborhood_baseline(mcp, address=DEMO_ADDRESS)).model_dump())
    finally:
        await mcp.aclose()
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
