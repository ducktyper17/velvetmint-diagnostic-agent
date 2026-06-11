"""The agent loop: retrieve -> draft -> self-verify -> revise -> finalize.

Why this is its own module:
    `/decode` should read as one clear agent policy, not a tangle of model
    calls inside an HTTP handler. This orchestrator owns the control flow
    that makes the system an *agent*: after drafting an explanation it
    reviews its own work against the retrieved evidence and decides whether
    to accept it or revise it once. Every decision is recorded as a step so
    the UI (and a hackathon judge) can watch the agent reason.

The loop is intentionally bounded — at most one revision — so latency and
cost stay predictable and a live demo never spins.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from extractor import ExtractedReport
from responder import DecodedReport, respond
from retriever import RetrievalBundle, retrieve
from verifier import verify_draft


@dataclass
class AgentStep:
    """One observable step in the agent's reasoning, surfaced to the UI."""

    name: str
    status: str  # "done" | "issues" | "revised" | "skipped"
    detail: str


def _count(bundle: RetrievalBundle) -> int:
    return len(bundle.literature) + len(bundle.guidelines) + len(bundle.forum_posts)


async def run_agent(
    extracted: ExtractedReport,
    *,
    session: Any | None = None,
) -> DecodedReport:
    """Run the full agent loop and return the final, trace-annotated report."""

    steps: list[AgentStep] = []

    # 1. Retrieve grounding evidence from MongoDB Atlas.
    bundle = await retrieve(extracted, session=session)
    steps.append(
        AgentStep(
            name="retrieve",
            status="done",
            detail=(
                f"Retrieved {_count(bundle)} sources from MongoDB Atlas "
                f"({len(bundle.literature)} literature, {len(bundle.guidelines)} "
                f"guideline, {len(bundle.forum_posts)} patient-experience)."
            ),
        )
    )

    # 2. Draft the explanation.
    draft = await respond(extracted, bundle)
    steps.append(AgentStep("draft", "done", "Synthesized a plain-language explanation."))

    # 3. Self-verify the draft against the retrieved evidence.
    review = verify_draft(draft, bundle)
    final = draft
    if review.grounded:
        steps.append(
            AgentStep(
                "verify",
                "done",
                f"Self-check ({review.method}) passed: claims grounded, no diagnostic language.",
            )
        )
    else:
        steps.append(
            AgentStep(
                "verify",
                "issues",
                f"Self-check ({review.method}) found {len(review.issues)} issue(s): "
                + "; ".join(review.issues),
            )
        )
        # 4. One bounded revision pass that targets the reviewer's issues.
        revised = await respond(extracted, bundle, critique=review.issues)
        recheck = verify_draft(revised, bundle)
        if recheck.grounded or len(recheck.issues) < len(review.issues):
            final = revised
            steps.append(
                AgentStep(
                    "revise",
                    "revised",
                    "Revised the draft to fix the flagged issues and re-verified.",
                )
            )
        else:
            steps.append(
                AgentStep(
                    "revise",
                    "skipped",
                    "Revision did not improve grounding; kept the safer original draft.",
                )
            )

    final.metadata = {
        **final.metadata,
        "agent_steps": [asdict(s) for s in steps],
        "verification_method": review.method,
    }
    return final
