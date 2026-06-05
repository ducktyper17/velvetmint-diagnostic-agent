"""One-shot smoke test for the VelvetMint SUT.

Drives a single user message through the SUT (no QA agent in the loop) so
you can verify the SUT boots, its tools are wired, and its turn is being
auto-traced into Phoenix. Used by ``make run-sut MESSAGE="..."``.

Importing ``qa_agent`` first triggers Phoenix tracer registration even
though the QA agent itself is not used here — that way the SUT turn shows
up in the same Phoenix project as a real audit.

Usage:
    cd 02-arize-mystery-shopper/agent
    uv run python scripts/smoke_sut.py --message "..."
"""

from __future__ import annotations

import argparse
import asyncio
import secrets

# Trigger Phoenix tracer registration (no-op if PHOENIX_API_KEY is unset).
import qa_agent  # noqa: F401
from google.adk.runners import InMemoryRunner
from google.genai import types

from sut.agent import root_agent


async def _run_once(message: str) -> None:
    app_name = "sut_smoke"
    user_id = "smoke-user"
    session_id = secrets.token_hex(4)

    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    new_message = types.Content(role="user", parts=[types.Part(text=message)])
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        print(event)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the VelvetMint SUT.")
    parser.add_argument(
        "--message",
        required=True,
        help="The user message to send to the SUT.",
    )
    args = parser.parse_args()
    asyncio.run(_run_once(args.message))


if __name__ == "__main__":
    main()
