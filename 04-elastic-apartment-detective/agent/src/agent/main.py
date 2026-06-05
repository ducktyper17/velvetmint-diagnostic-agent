"""FastAPI service for the Elastic Apartment Detective."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl, model_validator
from sse_starlette.sse import EventSourceResponse

from agent.agent_loop import AgentEvent, build_listing_context, run_agent_loop
from agent.config import Settings, get_settings
from agent.tools import ElasticMCPClient

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources once per process."""

    settings = get_settings()
    mcp = ElasticMCPClient(settings)
    app.state.settings = settings
    app.state.mcp = mcp
    log.info("apartment_detective.startup_complete", environment=settings.environment)
    try:
        yield
    finally:
        await mcp.aclose()


app = FastAPI(
    title="Elastic Apartment Detective",
    version="0.1.0",
    description=(
        "Investigates a rental listing with Elastic-backed evidence and returns "
        "a renter-risk brief."
    ),
    lifespan=lifespan,
)


class InvestigationRequest(BaseModel):
    """Body for `POST /investigate`."""

    listing_url: HttpUrl | None = None
    address: str | None = Field(default=None, min_length=5, max_length=200)
    question: str | None = Field(default=None, min_length=3, max_length=300)

    @model_validator(mode="after")
    def validate_input(self) -> "InvestigationRequest":
        """Require at least one way to identify the listing."""

        if self.listing_url is None and self.address is None:
            raise ValueError("provide `listing_url`, `address`, or both")
        return self


class HealthResponse(BaseModel):
    """Body for `GET /healthz`."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str
    demo_mode: bool


@app.get("/healthz", response_model=HealthResponse)
async def healthz(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Liveness probe for Cloud Run and local dev."""

    return HealthResponse(environment=settings.environment, demo_mode=settings.is_demo)


@app.post("/investigate")
async def investigate(
    body: InvestigationRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Stream one apartment investigation as SSE."""

    investigation_id = str(uuid.uuid4())
    mcp: ElasticMCPClient = request.app.state.mcp

    try:
        context = build_listing_context(
            address=body.address,
            listing_url=str(body.listing_url) if body.listing_url else None,
            question=body.question,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log.info(
        "apartment_detective.investigation_received",
        investigation_id=investigation_id,
        address=context.address,
        listing_source=context.source,
    )

    async def event_publisher() -> AsyncIterator[dict[str, Any]]:
        yield _sse_event(
            AgentEvent(
                type="thought",
                payload={
                    "text": "Starting apartment investigation...",
                    "investigation_id": investigation_id,
                },
                iteration=0,
            )
        )

        try:
            async for event in run_agent_loop(context=context, settings=settings, mcp=mcp):
                yield _sse_event(event)
        except Exception as exc:
            log.exception("apartment_detective.loop_crashed", error=str(exc))
            yield _sse_event(
                AgentEvent(
                    type="error",
                    payload={"error": f"investigation crashed: {exc}"},
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
    """Replay endpoint placeholder until persistence is wired."""

    if not investigation_id:
        raise HTTPException(status_code=400, detail="missing investigation_id")

    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "detail": "Elastic-backed brief persistence and replay are not wired yet.",
            "investigation_id": investigation_id,
        },
    )


def _sse_event(event: AgentEvent) -> dict[str, Any]:
    """Convert an agent event into the shape expected by sse-starlette."""

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
    """Run the API with uvicorn."""

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
