from __future__ import annotations

from fastapi.testclient import TestClient

from agent.config import get_settings


def _configure_env(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "rapid-agent-hack-2026")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("DYNATRACE_ENVIRONMENT_URL", "https://demo.apps.dynatrace.com")
    monkeypatch.setenv("DYNATRACE_MCP_URL", "http://localhost:3333")
    monkeypatch.setenv("DYNATRACE_MCP_TOKEN", "test-token")
    monkeypatch.setenv("STUB_GEMINI_RESPONSES", "true")
    monkeypatch.setenv("STUB_DYNATRACE_TOOLS", "true")
    get_settings.cache_clear()


def test_healthz_returns_service_metadata(monkeypatch) -> None:
    _configure_env(monkeypatch)

    from agent.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "environment": "local",
    }
