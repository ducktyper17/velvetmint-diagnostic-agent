from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_GEMINI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "offline-demo")
    monkeypatch.setenv("PROMPT_MODE", "bad")


def test_chat_bad_mode_reports_extra_tool_activity() -> None:
    from refund_assistant.main import app

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "I'm not sure if I'm eligible — maybe you can help?"},
            headers={
                "X-Prompt-Mode": "bad",
                "X-Release-Id": "release-2026-05-26-bad-prompt",
                "X-Prompt-Version": "v12",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_calls"] >= 2
    assert payload["prompt_mode"] == "bad"
    assert payload["release_id"] == "release-2026-05-26-bad-prompt"
