"""LLM-as-judge runner.

For each conversation we run six judges (one per dimension). Each judge call
becomes a row in a Phoenix experiment, so head-to-head comparisons across
targets are queryable in the Phoenix UI without our code in the loop.

The runner is deliberately small. The integration points marked TODO are:

1. Pulling the conversation transcript out of Phoenix by session id, so the
   judge sees exactly what the orchestrator saw.
2. Resolving the latest version of each judge prompt via the Phoenix MCP
   server (so the prompts in prompts.py are the seed, not the source of
   truth at runtime).
3. Calling Gemini 3 on Vertex AI with the resolved prompt + transcript.
4. Writing each (scenario, dimension) result into a Phoenix experiment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from prompts import PROMPT_BY_DIMENSION
from scenarios import Scenario, ScoringDimension


@dataclass
class DimensionScore:
    dimension: ScoringDimension
    score: float
    rationale: str
    prompt_version: str


@dataclass
class JudgeReport:
    session_id: str
    target_name: str
    scenario_id: str
    scores: list[DimensionScore] = field(default_factory=list)


async def run_judges_for_session(
    session_id: str,
    scenario: Scenario,
    target_name: str,
) -> JudgeReport:
    """Score one scenario run across all six dimensions.

    The function intentionally returns deterministic stubs in the scaffold so
    the FastAPI endpoint can be exercised end-to-end without Phoenix or Vertex
    AI credentials. Replace the stub body with real calls in the order marked.
    """

    # TODO(1): fetch the transcript from Phoenix.
    #
    # The orchestrator tags each scenario run with `session.id == session_id`,
    # so we can pull the full conversation back by sessions.get-session via
    # the MCP client. Until that wiring lands we operate on an empty list.
    transcript: list[dict[str, str]] = []

    scores: list[DimensionScore] = []
    for dimension, prompt in PROMPT_BY_DIMENSION.items():
        # TODO(2): replace with `get-latest-prompt` via the Phoenix MCP client
        # so the version we ran against is recorded in the experiment row.
        prompt_version = f"{prompt.name}:seed"

        # TODO(3): call Gemini 3 on Vertex AI with the rendered prompt and
        # the transcript. The shape we want back is:
        #   { "score": <float between 0.0 and 1.0>, "rationale": <str> }
        # parsed defensively (LLMs sometimes wrap JSON in fences).
        rendered = _render_prompt(prompt.template, scenario, transcript)
        _ = rendered  # silence unused warnings until the real call lands
        score, rationale = _stub_score(dimension)

        scores.append(
            DimensionScore(
                dimension=dimension,  # type: ignore[arg-type]
                score=score,
                rationale=rationale,
                prompt_version=prompt_version,
            )
        )

    # TODO(4): write the report into a Phoenix experiment for this audit job
    # using `list-experiments-for-dataset` to find-or-create the experiment,
    # then add one row per dimension via the experiment API.

    return JudgeReport(
        session_id=session_id,
        target_name=target_name,
        scenario_id=scenario.id,
        scores=scores,
    )


def _render_prompt(template: str, scenario: Scenario, transcript: list[dict[str, str]]) -> str:
    return template.format(
        conversation=json.dumps(transcript, indent=2),
        ground_truth=scenario.persona,
        escalation_expectation=", ".join(scenario.stop_when),
        brand_voice_guidelines="(brand voice unknown in scaffold; pulled per-target in MVP)",
        conversation_a="(paired-run not yet wired)",
        conversation_b="(paired-run not yet wired)",
    )


def _stub_score(dimension: str) -> tuple[float, str]:
    # Deterministic placeholders keep the endpoint end-to-end testable without
    # any external services. Real implementation returns real judge output.
    return (0.5, f"stub score for {dimension}; replace with real Gemini judge call")
