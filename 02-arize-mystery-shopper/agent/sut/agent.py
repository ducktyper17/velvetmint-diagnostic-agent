"""The VelvetMint customer-support ADK agent (the SUT).

A separate ADK ``Agent`` so the QA agent has a real Gemini agent to audit.
Tools are the mock VelvetMint domain primitives in ``sut/tools.py``. The
system instruction is the seed in ``sut/prompt.py`` — at runtime, the
``run_scenario`` tool fetches the **current** version of the prompt from
Phoenix so improvements made by the QA agent are picked up automatically.
"""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from sut.prompt import VELVETMINT_SUT_INSTRUCTION
from sut.tools import escalate_to_human, issue_refund, lookup_customer, lookup_order


def build_sut(instruction: str | None = None) -> Agent:
    """Build a fresh SUT agent.

    Why a factory instead of a module-level ``root_agent``: ``run_scenario``
    needs to instantiate one SUT per scenario with a specific system
    instruction (the version pulled from Phoenix), so a singleton is wrong.
    """

    return Agent(
        model=os.environ.get("SUT_MODEL", "gemini-2.5-flash"),
        name="velvetmint_support_sut",
        instruction=instruction or VELVETMINT_SUT_INSTRUCTION,
        tools=[
            FunctionTool(func=lookup_order),
            FunctionTool(func=lookup_customer),
            FunctionTool(func=issue_refund),
            FunctionTool(func=escalate_to_human),
        ],
    )


root_agent = build_sut()
