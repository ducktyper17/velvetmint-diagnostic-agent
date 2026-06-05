"""FastAPI service for the Blast Radius agent."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agent.agent_loop import AgentEvent, IncidentRequest, run_incident_loop
from agent.config import Settings, get_settings
from agent.scenario import get_default_vulnerability
from agent.tools import GitLabMCPClient


log = logging.getLogger(__name__)

def _resolve_static_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "static",
        Path.cwd() / "static",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


_STATIC_DIR = _resolve_static_dir()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize long-lived resources once per process."""

    settings = get_settings()
    app.state.settings = settings
    app.state.gitlab = GitLabMCPClient(settings)
    try:
        yield
    finally:
        await app.state.gitlab.aclose()


app = FastAPI(
    title="Blast Radius",
    version="0.1.0",
    description="GitLab-track zero-day response agent",
    lifespan=lifespan,
)

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class AnalyzeIncidentBody(BaseModel):
    """Request body for `POST /incidents/analyze`."""

    incident_title: str | None = Field(default=None, min_length=4, max_length=200)
    cve_id: str | None = Field(default=None, min_length=4, max_length=64)
    vulnerable_package: str | None = Field(default=None, min_length=1, max_length=100)
    fixed_version: str | None = Field(default=None, min_length=1, max_length=32)


class HealthResponse(BaseModel):
    """Response body for `GET /healthz`."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str
    demo_mode: bool
    gemini_summary_enabled: bool


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the incident dashboard."""

    dashboard = _STATIC_DIR / "index.html"
    return FileResponse(dashboard)


@app.get("/healthz", response_model=HealthResponse)
async def healthz(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return service health for Cloud Run or local dev."""

    return HealthResponse(
        environment=settings.environment,
        demo_mode=settings.is_demo,
        gemini_summary_enabled=settings.use_gemini_summary,
    )


@app.post("/incidents/analyze")
async def analyze_incident(
    body: AnalyzeIncidentBody,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Analyze an incoming vulnerability event and stream progress via SSE."""

    default_event = get_default_vulnerability()
    incident = IncidentRequest(
        incident_title=body.incident_title or default_event.incident_title,
        cve_id=body.cve_id or default_event.cve_id,
        vulnerable_package=body.vulnerable_package or default_event.vulnerable_package,
        fixed_version=body.fixed_version or default_event.fixed_version,
    )
    gitlab: GitLabMCPClient = request.app.state.gitlab

    async def event_publisher() -> AsyncIterator[dict[str, Any]]:
        yield _sse_event(
            AgentEvent(
                type="thought",
                payload={"text": "Starting incident analysis."},
                iteration=0,
            )
        )

        async for event in run_incident_loop(
            request=incident,
            settings=settings,
            gitlab=gitlab,
        ):
            yield _sse_event(event)

    return EventSourceResponse(
        event_publisher(),
        ping=15,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event: AgentEvent) -> dict[str, Any]:
    """Convert an `AgentEvent` into the format expected by SSE-Starlette."""

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
    """Start the local development server."""

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
