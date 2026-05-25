"""FastAPI service for the DTC Brand Health Diagnostic Agent.

Endpoints:

* ``GET  /healthz``         — Cloud Run liveness check.
* ``POST /diagnose``        — Kick off a diagnosis. Returns SSE stream.
* ``GET  /diagnoses/{id}``  — Read a stored diagnosis from MongoDB.

The SSE stream uses the same event shape as the agent loop's
:class:`AgentEvent` so the frontend (Next.js) can render reasoning, tool
calls, and the final report from a single ``EventSource``.
"""

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

from agent.agent_loop import AgentEvent, AgentRequest, run_agent_loop
from agent.config import Settings, get_settings
from agent.tools import FivetranMCPClient


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: open shared HTTP/Mongo clients once per process.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down per-process resources.

    Cloud Run keeps instances warm between requests, so the cost of the
    `httpx.AsyncClient` HTTP/2 handshake amortizes to ~0 across N requests.
    """
    settings = get_settings()
    mcp = FivetranMCPClient(settings)
    app.state.mcp = mcp
    app.state.settings = settings

    # TODO: open a MongoDB connection here. We use motor (async pymongo) once
    # the diagnosis-persistence work lands on Day 5.
    #     from motor.motor_asyncio import AsyncIOMotorClient
    #     app.state.mongo = AsyncIOMotorClient(settings.mongodb_uri.get_secret_value())

    log.info("agent.startup_complete", extra={"environment": settings.environment})
    try:
        yield
    finally:
        await mcp.aclose()
        # TODO: close mongo client when wired.


app = FastAPI(
    title="DTC Brand Health Diagnostic Agent",
    version="0.1.0",
    description=(
        "Autonomous DTC brand-health agent. Given a founder's question, sets "
        "up Fivetran connectors, syncs data into BigQuery, runs diagnostic "
        "queries, and returns a ranked root-cause report."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response schemas.
# ---------------------------------------------------------------------------


class DiagnoseRequest(BaseModel):
    """Body of ``POST /diagnose``."""

    question: str = Field(..., min_length=4, max_length=400)
    brand_id: str = Field(..., min_length=1, max_length=64)
    conversation_id: str | None = Field(
        default=None,
        description="Optional. Reuse to continue a prior conversation.",
    )


class HealthResponse(BaseModel):
    """Body of ``GET /healthz``."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str


# ---------------------------------------------------------------------------
# Endpoints.
# ---------------------------------------------------------------------------


@app.get("/healthz", response_model=HealthResponse)
async def healthz(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Cloud Run liveness probe."""
    return HealthResponse(environment=settings.environment)


@app.post("/diagnose")
async def diagnose(
    body: DiagnoseRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Kick off a diagnosis. Streams reasoning + tool calls back as SSE.

    The frontend opens this with a browser ``EventSource`` so each event
    surfaces in the dashboard live. Event types: ``thought``, ``tool_call``,
    ``tool_result``, ``final_report``, ``error``, ``done``.
    """
    conversation_id = body.conversation_id or str(uuid.uuid4())
    mcp: FivetranMCPClient = request.app.state.mcp

    agent_req = AgentRequest(
        question=body.question,
        brand_id=body.brand_id,
        conversation_id=conversation_id,
    )

    log.info(
        "agent.diagnose_received",
        extra={
            "conversation_id": conversation_id,
            "brand_id": body.brand_id,
        },
    )

    async def event_publisher() -> AsyncIterator[dict[str, Any]]:
        """Translate :class:`AgentEvent` -> SSE-Starlette event dicts."""
        # Send the conversation id up front so the client can subscribe to
        # `/diagnoses/{id}` later for replay.
        yield _sse_event(
            AgentEvent(
                type="thought",
                payload={"text": "Starting diagnosis...", "conversation_id": conversation_id},
                iteration=0,
            )
        )

        # TODO: write the user message + initial conversation row to MongoDB
        # before kicking off the loop. Right now we keep state in process.

        try:
            async for ev in run_agent_loop(
                request=agent_req,
                settings=settings,
                mcp=mcp,
            ):
                # TODO: persist each event in MongoDB so the diagnosis is
                # replayable from `/diagnoses/{id}`.
                yield _sse_event(ev)
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
        ping=15,  # keep the connection alive through Cloud Run's idle timeout
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx-style buffering
        },
    )


@app.get("/diagnoses/{diagnosis_id}")
async def get_diagnosis(diagnosis_id: str) -> JSONResponse:
    """Return a previously-stored diagnosis by id.

    TODO: read from MongoDB once persistence is wired (Day 5 of build plan).
    """
    if not diagnosis_id:
        raise HTTPException(status_code=400, detail="missing diagnosis_id")
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "detail": "MongoDB persistence is wired on Day 5 of the build plan.",
            "diagnosis_id": diagnosis_id,
        },
    )


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _sse_event(ev: AgentEvent) -> dict[str, Any]:
    """Convert an :class:`AgentEvent` into the dict shape sse-starlette wants.

    sse-starlette accepts ``{"event": str, "data": str, "id": str | None}``.
    We JSON-encode ``payload`` so the client can ``JSON.parse(e.data)``.
    """
    return {
        "event": ev.type,
        "data": json.dumps(
            {
                "iteration": ev.iteration,
                "ts_ms": ev.ts_ms,
                **ev.payload,
            }
        ),
    }


# ---------------------------------------------------------------------------
# Entrypoint.
# ---------------------------------------------------------------------------


def run() -> None:
    """Boot uvicorn. Wired as a project script in pyproject.toml.

    Cloud Run sets ``$PORT`` to 8080; locally we read it from settings.
    """
    settings = get_settings()
    uvicorn.run(
        "agent.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        # Cloud Run does not allow auto-reload in production.
        reload=settings.environment == "local",
    )


if __name__ == "__main__":
    run()
