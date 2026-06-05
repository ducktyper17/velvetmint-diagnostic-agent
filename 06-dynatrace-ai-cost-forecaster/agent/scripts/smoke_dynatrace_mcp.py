#!/usr/bin/env python3
"""Smoke-test the Dynatrace MCP gateway (tools/list + optional execute_dql)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def _load_env() -> None:
    agent_dir = Path(__file__).resolve().parents[1]
    load_dotenv(agent_dir / ".env")


def _post_json(*, url: str, token: str, method: str, params: dict | None = None) -> dict:
    payload: dict = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        payload["params"] = params
    response = httpx.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"MCP {method} failed: {body['error']}")
    return body.get("result", {})


def main() -> int:
    _load_env()
    url = os.environ.get("DYNATRACE_MCP_URL", "").strip()
    token = os.environ.get("DYNATRACE_MCP_TOKEN", "").strip()
    if not url or not token:
        print("Set DYNATRACE_MCP_URL and DYNATRACE_MCP_TOKEN in agent/.env")
        return 1

    print(f"mcp_url={url}")
    tools_result = _post_json(url=url, token=token, method="tools/list")
    tools = tools_result.get("tools") or tools_result.get("items") or tools_result
    if isinstance(tools, list):
        names = [tool.get("name", tool) for tool in tools[:20]]
        print(f"tools/list OK — showing up to 20: {names}")
    else:
        print("tools/list OK — raw result:")
        print(json.dumps(tools_result, indent=2)[:2000])

    if os.environ.get("SMOKE_RUN_DQL", "false").lower() != "true":
        print("Set SMOKE_RUN_DQL=true to also run a small execute_dql query.")
        return 0

    dql = 'fetch spans | limit 3'
    dql_result = _post_json(
        url=url,
        token=token,
        method="tools/call",
        params={"name": "execute_dql", "arguments": {"query": dql}},
    )
    print("execute_dql OK — preview:")
    print(json.dumps(dql_result, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
