"""FastAPI entrypoint for the Voice-AI Mystery Shopper agent.

This module wires together three concerns:

1. The HTTP surface (POST /audit kicks off a job; GET /audit/{id} polls it).
2. Phoenix OTel tracing setup, done once at startup so every downstream call
   inherits the tracer without per-call boilerplate.
3. The audit-job executor, kept deliberately minimal here. Real orchestration
   (Gemini 3 driving conversations, target adapters, Phoenix MCP calls) lives
   in helper modules and is stubbed at the integration points below.
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from judge import JudgeReport, run_judges_for_session
from scenarios import DEFAULT_SCENARIO_SET, Scenario


class Settings(BaseSettings):
    google_cloud_project: str = ""
    google_cloud_region: str = "us-central1"
    gemini_model_id: str = "gemini-3.0-pro"
    phoenix_collector_endpoint: str = "https://app.phoenix.arize.com"
    phoenix_api_key: str = ""
    phoenix_project_name: str = "mystery-shopper"
    audit_max_concurrency_per_target: int = 1
    audit_scenario_timeout_s: int = 120
    audit_max_turns: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


class Target(BaseModel):
    name: str
    kind: Literal["http", "websocket", "voice", "custom"]
    endpoint: str


class AuditRequest(BaseModel):
    targets: list[Target] = Field(..., min_length=1, max_length=10)
    scenario_set: str = "default-10"


class AuditJob(BaseModel):
    id: str
    created_at: datetime
    status: Literal["pending", "running", "complete", "failed"] = "pending"
    targets: list[Target]
    scenarios: list[Scenario]
    reports: list[JudgeReport] = Field(default_factory=list)
    error: str | None = None


# In-memory job store. Swapped for Firestore or Cloud SQL post-MVP. The dict
# is fine for a demo because Cloud Run keeps a single instance warm during a
# recorded audit and we don't need cross-instance durability for the video.
_JOBS: dict[str, AuditJob] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # TODO: configure the Phoenix OTel tracer here so every downstream LLM /
    # HTTP call is auto-instrumented. The call shape is roughly:
    #   from phoenix.otel import register
    #   register(project_name=settings.phoenix_project_name,
    #            endpoint=settings.phoenix_collector_endpoint,
    #            headers={"api_key": settings.phoenix_api_key})
    # Confirm the import path against the installed arize-phoenix version.
    yield


app = FastAPI(title="Voice-AI Mystery Shopper", lifespan=lifespan)


@app.post("/audit", status_code=202)
async def create_audit(req: AuditRequest, bg: BackgroundTasks) -> dict[str, str]:
    if req.scenario_set != "default-10":
        # The full 50-scenario set lives in Phoenix; only the bundled subset
        # is available without a Phoenix dataset id configured.
        raise HTTPException(status_code=400, detail="only default-10 ships in the scaffold")
    job = AuditJob(
        id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc),
        targets=req.targets,
        scenarios=DEFAULT_SCENARIO_SET,
    )
    _JOBS[job.id] = job
    bg.add_task(_run_audit, job.id)
    return {"id": job.id, "status": job.status}


@app.get("/audit/{job_id}")
async def get_audit(job_id: str) -> AuditJob:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="audit job not found")
    return job


@app.get("/audit/{job_id}/report")
async def get_report(job_id: str) -> list[JudgeReport]:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="audit job not found")
    if job.status != "complete":
        raise HTTPException(status_code=409, detail=f"job is {job.status}")
    return job.reports


async def _run_audit(job_id: str) -> None:
    job = _JOBS[job_id]
    job.status = "running"
    try:
        for target in job.targets:
            sem = asyncio.Semaphore(settings.audit_max_concurrency_per_target)
            async with sem:
                for scenario in job.scenarios:
                    # TODO: drive the conversation against `target` with Gemini 3 as
                    # the customer. Wrap each scenario in a Phoenix session id so
                    # the judge can pull the trace back by session.
                    session_id = f"{job.id}:{target.name}:{scenario.id}"
                    report = await run_judges_for_session(session_id, scenario, target.name)
                    job.reports.append(report)
        job.status = "complete"
    except Exception as exc:
        job.status = "failed"
        job.error = repr(exc)
