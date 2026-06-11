"""FastAPI entry point for the Doctor's Note Decoder.

Why this is intentionally thin:
    The agent's reasoning lives in extractor + retriever + responder.
    This file only does HTTP plumbing and the two service-level
    invariants:
      1. The MongoDB MCP server subprocess is up before the first request.
      2. Every response carries the legal disclaimer (enforced by the
         Pydantic schema; this layer just translates failures to 500s).
"""

from __future__ import annotations

import os
import shlex
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from extractor import extract_from_bytes, extract_from_text
from orchestrator import run_agent
from prompts import DISCLAIMER_PLAIN
from responder import DecodedReport

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bring up dependencies before serving traffic, tear down after.

    Uses stdio transport so the FastAPI service owns the MongoDB MCP
    subprocess directly in local dev and on Cloud Run.
    """

    stack = AsyncExitStack()
    app.state.mcp_session = None
    app.state.mcp_stack = stack
    try:
        command = os.getenv("MCP_SERVER_CMD", "npx")
        raw_args = os.getenv(
            "MCP_SERVER_ARGS",
            "-y mongodb-mcp-server --connection-string ${MONGODB_URI}",
        )
        args = [os.path.expandvars(arg) for arg in shlex.split(raw_args)]
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=os.environ.copy(),
        )
        try:
            read, write = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            app.state.mcp_session = session
        except Exception as exc:
            # Degrade gracefully: the service still serves the UI and /decode,
            # and retrieval falls back to a deterministic bundle. This keeps a
            # live demo from dying if the MCP subprocess or Atlas is flaky.
            print(f"[lifespan] MongoDB MCP unavailable, running degraded: {exc}")
        yield
    finally:
        await stack.aclose()


app = FastAPI(
    title="Doctor's Note Decoder",
    version="0.0.1",
    description=(
        "Explains medical reports in plain language. "
        "Does NOT diagnose. See LEGAL-DISCLAIMER.md."
    ),
    lifespan=lifespan,
)


_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    """Serve the single-page demo UI. Kept inline so the whole app is one
    Cloud Run service with no separate frontend build or CORS surface."""

    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "disclaimer": DISCLAIMER_PLAIN}


@app.post("/decode", response_model=DecodedReport)
async def decode(
    request: Request,
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> DecodedReport:
    """Decode a medical report into a structured plain-language explanation.

    Accepts either a `text` form field or a `file` upload (PDF or image).
    Exactly one must be present.
    """

    if (text is None) == (file is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of `text` or `file`.",
        )

    if text is not None:
        extracted = await extract_from_text(text)
    else:
        assert file is not None
        data = await file.read()
        extracted = await extract_from_bytes(
            data, mime_type=file.content_type or "application/octet-stream"
        )

    if not extracted.is_medical_report:
        raise HTTPException(
            status_code=422,
            detail="Input does not appear to be a medical report.",
        )

    return await run_agent(extracted, session=request.app.state.mcp_session)


@app.post("/vault/save")
async def vault_save(
    decoded: DecodedReport,
    token: Annotated[str, Form()],
) -> dict[str, str]:
    """Persist a DecodedReport to the per-user vault collection.

    The backup scaffold guards this with a static token. Real auth (OIDC
    + per-user namespacing on the Atlas side) is post-pivot work.
    """

    expected = os.getenv("DEMO_VAULT_TOKEN", "")
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Invalid vault token.")

    # TODO call MCP `insert-many` against MONGODB_COLLECTION_VAULT after
    # attaching a client-side Vertex embedding for the explanation text.
    # For the stub we just acknowledge.
    _ = decoded

    return {"status": "saved (stub)"}
