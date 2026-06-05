"""CLI + FastAPI entrypoint for the QA agent.

Three surfaces share this module:

1. **CLI** (``python -m qa_agent.main "audit velvetmint-support-v1"``):
   one ADK turn for quick smoke tests. Modeled on the canonical
   Arize hackathon reference repo's ``agent/main.py``.

2. **FastAPI** (``uvicorn qa_agent.main:app``): the deployed surface.
   - ``POST /audit`` kicks off an audit job (background task).
   - ``GET  /audit/{id}/events`` is an SSE stream of the QA agent's
     thinking. The frontend renders this in the live thinking panel.
   - ``GET  /audit/{id}/report`` returns the final delta report.
   - ``GET  /healthz`` for Cloud Run health checks.

3. **deterministic loop** via ``scripts/run_loop.py`` — runs the same
   six phases without the agent's reasoning, used as the demo-safety
   fallback path. The frontend can fetch ``out/delta_report.json`` to
   render the same final report whether the loop or the agent produced it.

Both API and CLI share the same ADK runner factory so behavior is
identical between local smoke tests and the deployed demo.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

import qa_agent  # noqa: F401  (triggers tracer registration)
from qa_agent.agent import root_agent


class AuditRequest(BaseModel):
    sut_id: str = "velvetmint-support-v1"
    scenario_set: str = "velvetmint-support.scenarios"
    mode: Literal["one_cycle", "multi_cycle"] = "one_cycle"


class AuditJob(BaseModel):
    id: str
    created_at: datetime
    status: Literal["pending", "running", "complete", "failed"] = "pending"
    sut_id: str
    scenario_set: str
    mode: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] | None = None
    error: str | None = None


_JOBS: dict[str, AuditJob] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Tracer is set up at import time; nothing else to boot."""
    yield


app = FastAPI(title="Self-Improving QA Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/audit", status_code=202)
async def create_audit(req: AuditRequest, bg: BackgroundTasks) -> dict[str, str]:
    job = AuditJob(
        id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc),
        sut_id=req.sut_id,
        scenario_set=req.scenario_set,
        mode=req.mode,
    )
    _JOBS[job.id] = job
    bg.add_task(_run_audit, job.id, req)
    return {"id": job.id, "status": job.status}


@app.get("/audit/{job_id}")
async def get_audit(job_id: str) -> AuditJob:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="audit job not found")
    return job


@app.get("/audit/{job_id}/events")
async def stream_events(job_id: str) -> EventSourceResponse:
    """Server-sent events stream of the QA agent's thinking trace.

    The frontend connects here and renders each event as a card in the
    live thinking panel. The stream closes when the job hits a terminal
    status (complete or failed).
    """

    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="audit job not found")

    async def _gen() -> AsyncIterator[dict[str, str]]:
        cursor = 0
        while True:
            current = _JOBS.get(job_id)
            if current is None:
                break
            while cursor < len(current.events):
                yield {"event": "thinking", "data": json.dumps(current.events[cursor])}
                cursor += 1
            if current.status in {"complete", "failed"}:
                final = {"status": current.status, "error": current.error}
                yield {"event": "done", "data": json.dumps(final)}
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(_gen())


@app.get("/audit/{job_id}/report")
async def get_report(job_id: str) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="audit job not found")
    if job.status not in {"complete", "failed"}:
        raise HTTPException(status_code=409, detail=f"job is {job.status}")
    return job.report or {}


@app.get("/loop/report")
async def get_loop_report() -> dict[str, Any]:
    """Serve the JSON report produced by ``scripts/run_loop.py``.

    The frontend falls back to this when the agent path hasn't run yet
    (or, in the demo's safety mode, when we want to render a known-good
    report instead of waiting for the agent to finish).
    """

    path = Path(__file__).resolve().parent.parent.parent / "out" / "delta_report.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="no loop report on disk yet")
    return json.loads(path.read_text())


async def _run_audit(job_id: str, req: AuditRequest) -> None:
    job = _JOBS[job_id]
    job.status = "running"
    try:
        report = await _run_qa_agent(
            job=job,
            user_text=(
                f"Run a full audit + one improvement cycle of SUT '{req.sut_id}'. "
                f"Use the Phoenix dataset '{req.scenario_set}'. "
                "Follow the six phases in your instructions."
            ),
        )
        job.report = report
        job.status = "complete"
    except Exception as exc:
        job.status = "failed"
        job.error = repr(exc)


async def _run_qa_agent(job: AuditJob, user_text: str) -> dict[str, Any]:
    """Boot an in-memory ADK runner and run the QA agent one turn.

    Returns a best-effort structured delta report parsed from the final
    agent message (the agent's instruction asks it to output JSON in the
    final reply). If the model emits plain prose, we fall back to a
    minimal report that just preserves the final text.
    """

    app_name = "self_improving_qa"
    user_id = "operator"
    session_id = secrets.token_hex(8)
    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=user_text)]),
    ):
        event_dict = _event_to_dict(event)
        job.events.append(event_dict)
        text = _extract_text(event)
        if text:
            final_text = text

    return _parse_report(final_text)


def _event_to_dict(event: Any) -> dict[str, Any]:
    """Best-effort event → dict serialization for the SSE / JSON surface."""

    try:
        if hasattr(event, "model_dump"):
            return event.model_dump(mode="json")
        return {"repr": repr(event)}
    except Exception as exc:  # pragma: no cover - defensive only
        return {"repr": repr(event), "serialize_error": repr(exc)}


def _extract_text(event: Any) -> str:
    """Pull the text content from an ADK event, if any."""

    content = getattr(event, "content", None)
    if content is None:
        return ""
    parts = getattr(content, "parts", None) or []
    return "\n".join(
        getattr(p, "text", "") for p in parts if getattr(p, "text", None)
    ).strip()


def _parse_report(text: str) -> dict[str, Any]:
    """Try to parse a JSON report out of the agent's final reply.

    The agent's instruction tells it to output a plain-text report, but we
    also accept JSON. If neither parses, we just preserve the text so the
    frontend has something to render.
    """

    if not text:
        return {"raw": "", "parsed": False}
    # Strip ``` fences if the model wrapped its reply.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return {**parsed, "parsed": True, "raw": text}
    except json.JSONDecodeError:
        pass
    return {"raw": text, "parsed": False}


def main_cli() -> None:
    """One-shot CLI run; pattern matches the Arize reference repo."""

    user_text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Run a full audit + one improvement cycle of SUT 'velvetmint-support-v1'."
    )
    job = AuditJob(
        id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc),
        sut_id="velvetmint-support-v1",
        scenario_set=os.environ.get("PHOENIX_SCENARIO_DATASET_NAME", "velvetmint-support.scenarios"),
        mode="one_cycle",
    )
    report = asyncio.run(_run_qa_agent(job=job, user_text=user_text))
    print(f"job_id={job.id} events={len(job.events)}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main_cli()
