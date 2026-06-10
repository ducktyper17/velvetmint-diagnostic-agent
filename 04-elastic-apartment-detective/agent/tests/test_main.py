"""Tests for the FastAPI surface."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("ELASTIC_MCP_URL", "http://localhost:3000/api/agent_builder/mcp")
os.environ.setdefault("ELASTIC_MCP_API_KEY", "test-key")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("STUB_GEMINI_RESPONSES", "true")

from agent.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_reports_demo_mode(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True


def test_investigate_requires_a_listing(client: TestClient) -> None:
    resp = client.post("/investigate", json={})
    assert resp.status_code == 422  # neither listing_url nor address provided


def test_investigate_streams_a_final_report(client: TestClient) -> None:
    resp = client.post(
        "/investigate",
        json={
            "listing_url": "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002"
        },
    )
    assert resp.status_code == 200
    body = resp.text
    assert "event: final_report" in body
    assert "event: done" in body
    assert "risk_score" in body
