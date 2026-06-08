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
    num_cycles = int(os.environ.get("AUDIT_NUM_CYCLES", "2"))

    print("=" * 60)
    print(f"Self-Improving QA Agent — multi-cycle audit ({audit_job_id})")
    print(f"  scenarios:      {len(DEFAULT_SCENARIO_SET)}")
    print(f"  judge replicas: {os.environ.get('AUDIT_JUDGE_REPLICAS', '3')}")
    print(f"  cycles:         {num_cycles}")
    print("=" * 60)

    # Run sequence: v1 (original) -> mutate -> v2 (cycle 1 fix) -> mutate -> v3 (cycle 2 fix) ...
    runs: list[dict[str, Any]] = []
    mutations: list[dict[str, Any]] = []
    current_prompt = VELVETMINT_SUT_INSTRUCTION

    # Initial baseline run (v1, original SUT prompt)
    print("\n[v1] Baseline run with original SUT prompt")
    baseline = await _run_all("baseline", audit_job_id)
    runs.append({"label": "v1", "results": baseline, "prompt": current_prompt})
    (OUT_DIR / "baseline.json").write_text(json.dumps(baseline, indent=2))

    for cycle in range(1, num_cycles + 1):
        print(f"\n=== Cycle {cycle} ===")
        prev = runs[-1]["results"]
        rationales = _failing_rationales(prev)
        print(f"  failing rationales: {len(rationales)}")
        if not rationales:
            print("  No failures left to address — stopping early.")
            break

        cluster_out = cluster_failures(rationales)
        clusters = cluster_out.get("clusters", [])
        if not clusters:
            print("  Cluster step returned no clusters — stopping.")
            break
        top = clusters[0]
        print(f"  top cluster: {top.get('name', '?')} (count={top.get('count', 0)}, "
              f"dims={top.get('dimensions_affected', [])})")
        (OUT_DIR / f"clusters-cycle{cycle}.json").write_text(json.dumps(cluster_out, indent=2))

        mutation = mutate_sut_prompt(cluster=top, current_prompt=current_prompt)
        if mutation.get("error"):
            print(f"  mutate failed: {mutation['error']} — stopping.")
            break
        print(f"  appended: {mutation['appended'][:140]}")
        mutations.append({"cycle": cycle, "cluster": top, "mutation": mutation})
        (OUT_DIR / f"mutation-cycle{cycle}.json").write_text(json.dumps(mutation, indent=2))

        current_prompt = mutation["new_prompt"]
        os.environ["ACTIVE_SUT_PROMPT_TEXT"] = current_prompt

        version_label = f"v{cycle + 1}-cycle{cycle}-fix"
        print(f"\n[v{cycle + 1}] Re-run scenarios with cycle-{cycle} fix applied")
        cycle_results = await _run_all(version_label, audit_job_id)
        runs.append({"label": f"v{cycle + 1}", "results": cycle_results, "prompt": current_prompt})
        (OUT_DIR / f"v{cycle + 1}.json").write_text(json.dumps(cycle_results, indent=2))

    # Per-cycle deltas + overall delta
    per_cycle_deltas: list[dict[str, Any]] = []
    for i in range(1, len(runs)):
        d = _compute_delta(runs[i - 1]["results"], runs[i]["results"])
        per_cycle_deltas.append({
            "from": runs[i - 1]["label"],
            "to":   runs[i]["label"],
            "delta": d,
        })
    overall_delta = _compute_delta(runs[0]["results"], runs[-1]["results"])

    # Build report; preserve legacy single-cycle keys so the frontend / API
    # remain backward-compatible.
    legacy_top_cluster = mutations[0]["cluster"] if mutations else None
    legacy_mutation = mutations[0]["mutation"] if mutations else None

    report = {
        "audit_job_id": audit_job_id,
        "scenario_count": len(DEFAULT_SCENARIO_SET),
        "num_cycles_run": len(mutations),

        # Multi-cycle keys
        "mutations":        mutations,
        "per_cycle_deltas": per_cycle_deltas,
        "overall_delta":    overall_delta,
        "pass_rates":       {r["label"]: _pass_rate(r["results"]) for r in runs},
        "run_labels":       [r["label"] for r in runs],

        # Legacy single-cycle keys (frontend / API still consume these)
        "top_cluster":        legacy_top_cluster,
        "mutation":           legacy_mutation,
        "delta":              overall_delta,
        "baseline_pass_rate": _pass_rate(runs[0]["results"]) if runs else 0.0,
        "post_fix_pass_rate": _pass_rate(runs[-1]["results"]) if runs else 0.0,
    }
    # Also write a legacy post_fix.json pointing at the final run
    if runs:
        (OUT_DIR / "post_fix.json").write_text(json.dumps(runs[-1]["results"], indent=2))
    (OUT_DIR / "delta_report.json").write_text(json.dumps(report, indent=2))

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print("\nPass rates per version:")
    for label, rate in report["pass_rates"].items():
        print(f"  {label}: {rate:.0%}")

    for cycle_delta in per_cycle_deltas:
        print(f"\nDelta {cycle_delta['from']} -> {cycle_delta['to']}:")
        _print_delta_block(cycle_delta["delta"])

    if len(runs) > 2:
        print(f"\nOverall delta {runs[0]['label']} -> {runs[-1]['label']}:")
        _print_delta_block(overall_delta)


def _print_delta_block(delta_per_dim: dict[str, dict[str, Any]]) -> None:
    """Print a per-dimension delta block, marking improvements with ✓.

    Hallucination is inverted (higher = worse), so a NEGATIVE delta is an
    improvement there. All other dimensions are normal (positive = improvement).
    """
    for dim, d in delta_per_dim.items():
        if d.get("delta") is None:
            continue
        delta = d["delta"]
        is_inverted = dim == "hallucination"
        improved = (delta < 0 if is_inverted else delta > 0) and abs(delta) > 0.001
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "·")
        mark = "  ✓" if improved else ""
        print(
            f"  {dim:<14} {arrow} delta={delta:+.3f} "
            f"({d['baseline_mean']:.2f} → {d['post_fix_mean']:.2f}, "
            f"n={d['n']}, p={d['p_value']}){mark}"
        )


def _pass_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("passed")) / len(rows)


if __name__ == "__main__":
    asyncio.run(main())
