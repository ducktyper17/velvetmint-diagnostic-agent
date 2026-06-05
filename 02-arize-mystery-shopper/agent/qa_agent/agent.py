"""QA agent — root ADK Agent with tools and Phoenix MCP toolset.

The agent's behavior comes from three places:

1. ``QA_AGENT_INSTRUCTION`` in ``qa_agent.prompt`` — the phased instruction.
2. The three ``FunctionTool``s defined in ``qa_agent.tools.*`` — the domain
   primitives ``run_scenario``, ``cluster_failures``, ``mutate_sut_prompt``.
3. The ``McpToolset`` for ``@arizeai/phoenix-mcp`` — exposes the full
   Phoenix MCP surface (list-traces, get-spans, upsert-prompt, etc.) to
   the agent as runtime tools. This is the critical line: it's what
   makes the "agent introspects its own traces at runtime" claim real.

We deliberately do NOT also expose a ``run_experiment`` tool — the QA
agent commits experiment rows by calling Phoenix MCP directly. Fewer
custom tools means the agent's reasoning leans harder on Phoenix's
canonical surface, which is the demo story.
"""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from qa_agent.prompt import QA_AGENT_INSTRUCTION
from qa_agent.tools.cluster import cluster_failures
from qa_agent.tools.mutate import mutate_sut_prompt
from qa_agent.tools.scenarios import run_scenario


def _phoenix_mcp_toolset() -> McpToolset:
    """Wire the Phoenix MCP server into ADK as a toolset.

    Reads ``PHOENIX_API_KEY`` and ``PHOENIX_COLLECTOR_ENDPOINT`` so the
    spawned ``@arizeai/phoenix-mcp@latest`` subprocess can authenticate.
    The ``--baseUrl`` value must include the ``/s/<space>`` segment when
    using Phoenix Cloud — same constraint as the OTel exporter.

    Canonical ADK 1.32+ API: McpToolset(connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(...))). See
    https://adk.dev/tools-custom/mcp-tools/
    """

    api_key = os.environ.get("PHOENIX_API_KEY", "")
    base_url = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
    command = os.environ.get("PHOENIX_MCP_COMMAND", "npx")
    extra_args = os.environ.get("PHOENIX_MCP_ARGS", "-y,@arizeai/phoenix-mcp@latest")
    args = [a for a in extra_args.split(",") if a]
    if base_url:
        args.extend(["--baseUrl", base_url])
    if api_key:
        args.extend(["--apiKey", api_key])
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=command, args=args),
        ),
    )


root_agent = Agent(
    model=os.environ.get("QA_MODEL", "gemini-2.5-pro"),
    name="qa_agent",
    instruction=QA_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=run_scenario),
        FunctionTool(func=cluster_failures),
        FunctionTool(func=mutate_sut_prompt),
        _phoenix_mcp_toolset(),
    ],
)
