from __future__ import annotations

from fastapi.testclient import TestClient

from agent.main import app


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "demo_mode" in body
