"""Subject Under Test (SUT) — a deliberately-flawed VelvetMint support agent.

The SUT is a separate ADK ``Agent`` running on Gemini 2.5 Flash. It exists
purely to give the QA agent something concrete to audit and improve. Its
system prompt is intentionally bad in three specific ways (documented in
``sut/prompt.py``); the demo's payoff is the QA agent discovering and
patching one or more of those flaws.

Why a separate agent (and not a fake HTTPS endpoint): keeping the SUT as
an in-repo ADK agent means a) its turns are auto-traced into the same
Phoenix project as the QA agent, b) the QA agent can rewrite its prompt
via Phoenix MCP ``upsert-prompt`` and the new version is picked up by
``run_scenario`` on the next call, with zero deployment.
"""
