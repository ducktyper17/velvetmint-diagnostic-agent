"""FastAPI service for Agent Reliability Guard."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agent.agent_loop import AgentEvent, AgentRequest, run_agent_loop, run_replay
from agent.config import Settings, get_settings
from agent.tools import DynatraceMCPClient


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down shared clients."""

    settings = get_settings()
    mcp = DynatraceMCPClient(settings)
    app.state.mcp = mcp
    app.state.settings = settings

    log.info("agent.startup_complete", extra={"environment": settings.environment})
    try:
        yield
    finally:
        await mcp.aclose()


app = FastAPI(
    title="Agent Reliability Guard",
    version="0.1.0",
    description=(
        "Investigates regressions in Gemini-powered applications by querying "
        "Dynatrace telemetry, running change analysis, and publishing an "
        "operator-facing response."
    ),
    lifespan=lifespan,
)


class InvestigateRequest(BaseModel):
    """Body of POST /investigate."""

    question: str = Field(..., min_length=8, max_length=500)
    service_name: str = Field(..., min_length=1, max_length=100)
    release_id: str | None = Field(default=None, max_length=100)
    lookback_minutes: int | None = Field(default=None, ge=5, le=1440)
    conversation_id: str | None = Field(
        default=None,
        description="Optional. Reuse to continue a prior investigation.",
    )
    replay: bool = Field(
        default=False,
        description=(
            "Run the deterministic, paced offline replay instead of a live "
            "investigation. Bulletproof fallback for on-stage demos."
        ),
    )


class HealthResponse(BaseModel):
    """Body of GET /healthz."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str


@app.get("/healthz", response_model=HealthResponse)
async def healthz(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Cloud Run liveness probe."""

    return HealthResponse(environment=settings.environment)


@app.post("/investigate")
async def investigate(
    body: InvestigateRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Kick off an investigation and stream events as SSE."""

    conversation_id = body.conversation_id or str(uuid.uuid4())
    mcp: DynatraceMCPClient = request.app.state.mcp

    agent_request = AgentRequest(
        question=body.question,
        service_name=body.service_name,
        release_id=body.release_id,
        lookback_minutes=body.lookback_minutes or settings.lookback_minutes_default,
        conversation_id=conversation_id,
    )

    # demo_mode forces replay globally; the per-request flag opts in case by case.
    use_replay = body.replay or settings.demo_mode

    log.info(
        "agent.investigate_received",
        extra={
            "conversation_id": conversation_id,
            "service_name": body.service_name,
            "release_id": body.release_id,
            "replay": use_replay,
        },
    )

    async def event_publisher() -> AsyncIterator[dict[str, Any]]:
        yield _sse_event(
            AgentEvent(
                type="thought",
                payload={"text": "Starting investigation...", "conversation_id": conversation_id},
                iteration=0,
            )
        )

        events = (
            run_replay(request=agent_request, settings=settings)
            if use_replay
            else run_agent_loop(request=agent_request, settings=settings, mcp=mcp)
        )
        try:
            async for event in events:
                yield _sse_event(event)
        except Exception as exc:
            log.exception("agent.loop_crashed")
            yield _sse_event(
                AgentEvent(
                    type="error",
                    payload={"error": f"agent crashed: {exc}"},
                    iteration=-1,
                )
            )

    return EventSourceResponse(
        event_publisher(),
        ping=15,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str) -> JSONResponse:
    """Return a previously stored investigation.

    TODO: wire persistence once we decide whether replay lives in MongoDB,
    Firestore, or a file-backed demo cache.
    """

    if not investigation_id:
        raise HTTPException(status_code=400, detail="missing investigation_id")
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "detail": "Investigation persistence has not been wired yet.",
            "investigation_id": investigation_id,
        },
    )


def _sse_event(event: AgentEvent) -> dict[str, Any]:
    """Convert an AgentEvent into the dict shape sse-starlette expects."""

    return {
        "event": event.type,
        "data": json.dumps(
            {
                "iteration": event.iteration,
                "ts_ms": event.ts_ms,
                **event.payload,
            }
        ),
    }


def run() -> None:
    """Boot uvicorn. Wired as a project script in pyproject.toml."""

    settings = get_settings()
    uvicorn.run(
        "agent.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "local",
    )


if __name__ == "__main__":
    run()
