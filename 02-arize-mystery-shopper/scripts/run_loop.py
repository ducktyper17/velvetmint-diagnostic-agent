"""Deterministic end-to-end audit loop.

What this script does (the same six phases as the agent's instruction, but
driven by code so we always have a reproducible demo path):

  1. Baseline run: every scenario through the SUT, score with 6 judges × N
     replicas, write the per-(scenario, dimension) rows to ``out/baseline.json``.
  2. Introspect: collect all failing (dim < 0.5) rows.
  3. Cluster: call ``cluster_failures`` → 1-3 named clusters.
  4. Mutate: call ``mutate_sut_prompt`` against the top cluster.
  5. Activate: write the new prompt text to ``ACTIVE_SUT_PROMPT_TEXT`` (in-
     process env var) so subsequent ``run_scenario`` calls use it.
  6. Post-fix run: re-run all scenarios with the new prompt, score the same
     way, write ``out/post_fix.json``.
  7. Delta report: compute per-dimension mean delta + a paired Wilcoxon
     p-value (over per-scenario per-dimension medians). Write
     ``out/delta_report.json`` for the frontend to render.

Run:
    cd 02-arize-mystery-shopper/agent
    uv run python ../scripts/run_loop.py
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from dotenv import load_dotenv

load_dotenv(AGENT_DIR / ".env")

import qa_agent  # noqa: F401, E402 — triggers tracer registration

from qa_agent.tools.cluster import cluster_failures  # noqa: E402
from qa_agent.tools.mutate import mutate_sut_prompt  # noqa: E402
from qa_agent.tools.scenarios import run_scenario  # noqa: E402
from scenarios import DEFAULT_SCENARIO_SET  # noqa: E402
from sut.prompt import VELVETMINT_SUT_INSTRUCTION  # noqa: E402


OUT_DIR = AGENT_DIR.parent / "out"
DIMENSIONS = ["empathy", "accuracy", "escalation", "bias", "hallucination", "brand_voice"]


async def _run_all(version_label: str, audit_job_id: str) -> list[dict[str, Any]]:
    """Run every scenario at given prompt version. Bounded concurrency."""

    max_concurrency = int(os.environ.get("AUDIT_MAX_CONCURRENCY", "4"))
    sem = asyncio.Semaphore(max_concurrency)
    results: list[dict[str, Any]] = []

    async def _one(scenario_id: str) -> None:
        async with sem:
            print(f"  [{version_label}] running {scenario_id} ...", flush=True)
            row = await run_scenario(
                scenario_id=scenario_id,
                sut_prompt_version=version_label,
                audit_job_id=audit_job_id,
            )
            results.append(row)

    await asyncio.gather(*(_one(s.id) for s in DEFAULT_SCENARIO_SET))
    results.sort(key=lambda r: r.get("scenario_id", ""))
    return results


def _failing_rationales(scenario_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten failing (dim < 0.5) per-dimension rows for clustering."""

    flat: list[dict[str, Any]] = []
    for row in scenario_rows:
        if row.get("error"):
            continue
        for score in row.get("scores", []):
            if score.get("median_score", 1.0) < 0.5:
                flat.append(
                    {
                        "session_id": row.get("phoenix_session_id", ""),
                        "scenario_id": row.get("scenario_id", ""),
                        "dimension": score["dimension"],
                        "score": score["median_score"],
                        "rationale": score.get("rationale_excerpt", ""),
                    }
                )
    return flat


def _compute_delta(
    baseline: list[dict[str, Any]],
    post_fix: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-dimension mean delta + a Wilcoxon-ish paired sign-rank p-value.

    We avoid scipy at runtime by computing a very simple sign-rank
    approximation. For the demo the absolute p-value matters less than
    the sign of the delta and the magnitude.
    """

    by_scenario_baseline = {r["scenario_id"]: r for r in baseline}
    by_scenario_post = {r["scenario_id"]: r for r in post_fix}
    shared = sorted(set(by_scenario_baseline) & set(by_scenario_post))

    per_dim: dict[str, dict[str, Any]] = {}
    for dim in DIMENSIONS:
        deltas: list[float] = []
        base_scores: list[float] = []
        post_scores: list[float] = []
        for sid in shared:
            b = _dim_score(by_scenario_baseline[sid], dim)
            p = _dim_score(by_scenario_post[sid], dim)
            if b is None or p is None:
                continue
            base_scores.append(b)
            post_scores.append(p)
            deltas.append(p - b)
        if not deltas:
            per_dim[dim] = {
                "baseline_mean": None,
                "post_fix_mean": None,
                "delta": None,
                "p_value": None,
                "n": 0,
            }
            continue
        per_dim[dim] = {
            "baseline_mean": round(_mean(base_scores), 3),
            "post_fix_mean": round(_mean(post_scores), 3),
            "delta": round(_mean(deltas), 3),
            "p_value": round(_sign_test_p_value(deltas), 3),
            "n": len(deltas),
        }
    return per_dim


def _dim_score(row: dict[str, Any], dim: str) -> float | None:
    for s in row.get("scores", []):
        if s.get("dimension") == dim:
            return float(s.get("median_score", 0.5))
    return None


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sign_test_p_value(deltas: list[float]) -> float:
    """Two-sided sign test p-value. Cheap approximation of Wilcoxon.

    Ignores ties. Returns 1.0 for fewer than 2 non-zero deltas.
    """

    nonzero = [d for d in deltas if abs(d) > 1e-6]
    if len(nonzero) < 2:
        return 1.0
    positives = sum(1 for d in nonzero if d > 0)
    n = len(nonzero)
    # Binomial two-sided
    k = max(positives, n - positives)
    p = sum(_binom(n, i) for i in range(k, n + 1)) / (2 ** n) * 2
    return min(1.0, max(0.0, p))


def _binom(n: int, k: int) -> int:
    return math.comb(n, k)


async def main() -> None:
    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    if not api_key:
        sys.exit("PHOENIX_API_KEY is unset. Cannot run the loop without Phoenix.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_job_id = os.environ.get("AUDIT_JOB_ID") or f"loop-{os.getpid()}"

    print("=" * 60)
    print(f"Self-Improving QA Agent — run_loop ({audit_job_id})")
    print(f"  scenarios: {len(DEFAULT_SCENARIO_SET)}")
    print(f"  judge replicas: {os.environ.get('AUDIT_JUDGE_REPLICAS', '3')}")
    print("=" * 60)

    # Phase 1: baseline
    print("\n[Phase 1] Baseline run")
    baseline = await _run_all("baseline", audit_job_id)
    (OUT_DIR / "baseline.json").write_text(json.dumps(baseline, indent=2))

    # Phase 2-3: introspect + cluster
    print("\n[Phase 2-3] Cluster failures")
    rationales = _failing_rationales(baseline)
    cluster_out = cluster_failures(rationales)
    clusters = cluster_out.get("clusters", [])
    print(f"  found {len(clusters)} cluster(s); top counts: " + ", ".join(
        f"{c.get('name', '?')}={c.get('count', 0)}" for c in clusters
    ))
    (OUT_DIR / "clusters.json").write_text(json.dumps(cluster_out, indent=2))

    if not clusters:
        print("\nNo failures found in baseline. The SUT is already perfect (?) — stopping.")
        return

    # Phase 4: mutate
    print("\n[Phase 4] Mutate SUT prompt")
    top_cluster = clusters[0]
    mutation = mutate_sut_prompt(cluster=top_cluster, current_prompt=VELVETMINT_SUT_INSTRUCTION)
    if mutation.get("error"):
        print(f"  mutate failed: {mutation['error']}")
        return
    print(f"  rationale: {mutation['rationale'][:160]}")
    print(f"  appended:  {mutation['appended'][:160]}")
    (OUT_DIR / "mutation.json").write_text(json.dumps(mutation, indent=2))

    # Phase 5: activate new prompt for subsequent runs
    new_prompt = mutation["new_prompt"]
    os.environ["ACTIVE_SUT_PROMPT_TEXT"] = new_prompt

    # Phase 6: post-fix run
    print("\n[Phase 6] Post-fix run")
    post_fix = await _run_all("post-fix", audit_job_id)
    (OUT_DIR / "post_fix.json").write_text(json.dumps(post_fix, indent=2))

    # Phase 7: delta
    print("\n[Phase 7] Delta report")
    delta_per_dim = _compute_delta(baseline, post_fix)
    report = {
        "audit_job_id": audit_job_id,
        "scenario_count": len(DEFAULT_SCENARIO_SET),
        "top_cluster": top_cluster,
        "mutation": mutation,
        "delta": delta_per_dim,
        "baseline_pass_rate": _pass_rate(baseline),
        "post_fix_pass_rate": _pass_rate(post_fix),
    }
    (OUT_DIR / "delta_report.json").write_text(json.dumps(report, indent=2))

    print("\nResult:")
    print(f"  baseline pass rate : {report['baseline_pass_rate']:.0%}")
    print(f"  post-fix pass rate : {report['post_fix_pass_rate']:.0%}")
    for dim, d in delta_per_dim.items():
        if d["delta"] is None:
            continue
        arrow = "↑" if d["delta"] > 0 else ("↓" if d["delta"] < 0 else "·")
        print(
            f"  {dim:<14} {arrow} delta={d['delta']:+.3f} "
            f"({d['baseline_mean']:.2f} → {d['post_fix_mean']:.2f}, n={d['n']}, p={d['p_value']})"
        )


def _pass_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("passed")) / len(rows)


if __name__ == "__main__":
    asyncio.run(main())
