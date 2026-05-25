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
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from extractor import extract_from_bytes, extract_from_text
from prompts import DISCLAIMER_PLAIN
from responder import DecodedReport, respond
from retriever import retrieve

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bring up dependencies before serving traffic, tear down after.

    TODO start the MongoDB MCP server subprocess here (using the
    `mcp` Python client and the MCP_SERVER_CMD / MCP_SERVER_ARGS env
    vars). For the backup scaffold we leave a hook so that wiring it
    is a one-file change.
    """

    app.state.mcp_session = None  # populated when MCP is wired
    yield
    # No teardown needed in the stub.


app = FastAPI(
    title="Doctor's Note Decoder",
    version="0.0.1",
    description=(
        "Explains medical reports in plain language. "
        "Does NOT diagnose. See LEGAL-DISCLAIMER.md."
    ),
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "disclaimer": DISCLAIMER_PLAIN}


@app.post("/decode", response_model=DecodedReport)
async def decode(
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

    bundle = await retrieve(extracted)
    return await respond(extracted, bundle)


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

    # TODO call MCP `insert-many` against MONGODB_COLLECTION_VAULT, with
    # auto-embedding (when VOYAGE_API_KEY is set the MCP server will
    # embed text fields automatically on insert). For the stub we just
    # acknowledge.
    _ = decoded

    return {"status": "saved (stub)"}
