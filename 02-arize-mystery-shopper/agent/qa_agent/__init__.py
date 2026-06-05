"""QA agent — the Gemini 2.5 Pro ADK agent that audits the SUT.

The root agent and its tool surface are defined in ``qa_agent.agent``.
Tracing setup lives in ``qa_agent.instrumentation`` and is initialized
once at import time so any module that imports ``qa_agent`` gets the
Phoenix OTel tracer wired automatically.
"""

from __future__ import annotations

from qa_agent.instrumentation import setup_tracing

setup_tracing()
