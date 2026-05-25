"""DTC Brand Health Diagnostic Agent.

Top-level package. Public entrypoints:

* :mod:`agent.main`              — FastAPI app + uvicorn `run` helper
* :mod:`agent.agent_loop`        — ReAct-style orchestration loop
* :mod:`agent.tools`             — Fivetran MCP + BigQuery tool wrappers
* :mod:`agent.diagnostic_engine` — Cross-platform analytical battery
* :mod:`agent.prompts`           — System prompt + few-shot examples
* :mod:`agent.config`            — Pydantic-Settings runtime configuration
"""

__version__ = "0.1.0"
