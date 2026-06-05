"""Grounding documents for Agent Builder data-store parity in local/demo mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _resolve_data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "data",
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


_DATA_DIR = _resolve_data_dir()


def _load_json(name: str) -> dict[str, Any]:
    path = _DATA_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_service_catalog() -> dict[str, Any]:
    """Return the service catalog used for blast-radius scoring."""

    return _load_json("service-catalog.json")


def load_runbooks() -> dict[str, Any]:
    """Return incident runbooks and patch policies."""

    return _load_json("runbooks.json")


def render_grounding_context() -> str:
    """Flatten grounding docs into a prompt block for Gemini."""

    catalog = load_service_catalog()
    runbooks = load_runbooks()
    services = catalog.get("services", [])
    policies = runbooks.get("patch_policies", [])

    service_lines = "\n".join(
        f"- {svc.get('service_name')}: tier={svc.get('tier')}, "
        f"owner={svc.get('owner')}, internet_facing={svc.get('internet_facing')}"
        for svc in services
    )
    policy_lines = "\n".join(
        f"- {policy.get('name')}: {policy.get('rule')}" for policy in policies
    )

    return (
        "SERVICE CATALOG\n"
        f"{service_lines or '- (empty)'}\n\n"
        "PATCH POLICIES\n"
        f"{policy_lines or '- (empty)'}"
    )
