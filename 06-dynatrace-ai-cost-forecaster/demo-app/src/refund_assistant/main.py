"""HTTP entrypoint for the refund assistant demo workload."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, Header
from pydantic import BaseModel, Field

from refund_assistant.assistant import ChatSettings, load_settings_from_env, run_chat
from refund_assistant.telemetry import setup_telemetry


setup_telemetry()

app = FastAPI(
    title="Refund Assistant",
    version="0.1.0",
    description="Gemini demo workload for Agent Reliability Guard",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    tool_calls: int
    input_tokens: int
    output_tokens: int
    latency_ms: int
    release_id: str
    prompt_version: str
    prompt_mode: str


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "refund-assistant"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    release_id: str | None = Header(default=None, alias="X-Release-Id"),
    prompt_version: str | None = Header(default=None, alias="X-Prompt-Version"),
    prompt_mode: str | None = Header(default=None, alias="X-Prompt-Mode"),
) -> ChatResponse:
    """Run one traced chat turn."""

    base = load_settings_from_env()
    resolved_mode: str = base.prompt_mode
    if prompt_mode:
        resolved_mode = "bad" if prompt_mode.strip().lower() == "bad" else "healthy"
    settings = ChatSettings(
        prompt_mode=resolved_mode,  # type: ignore[arg-type]
        release_id=release_id or base.release_id,
        prompt_version=prompt_version or base.prompt_version,
        model=base.model,
        project=base.project,
        location=base.location,
        stub_gemini=base.stub_gemini,
    )

    result = await run_chat(message=body.message, settings=settings)
    return ChatResponse(
        reply=result.reply,
        tool_calls=result.tool_calls,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        release_id=settings.release_id,
        prompt_version=settings.prompt_version,
        prompt_mode=settings.prompt_mode,
    )


def run() -> None:
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run("refund_assistant.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    run()
