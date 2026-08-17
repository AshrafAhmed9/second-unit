"""THE PROOF — run N seeded conditions across the failure classes, score the
agent against a threshold-alerting baseline, and commit a regenerable
scorecard to eval/RESULTS.md. No sampled past hackathon winner shipped this;
it is the cheapest available edge over the rest of the field.

Two modes:
  --dry-run   Uses fixtures/eval_conditions.json + a scripted "agent" so the
              harness and scoring logic are testable right now, with no live
              Grafana/Gemini/Cloud Run dependency. This is what CI runs.
  (default)   Dispatches a real backlot render per condition (backlot/dispatch.py),
              triggers a real agent run against the deployed service, and
              scores the ACTUAL detection outcome. This is what produces the
              real eval/RESULTS.md committed for judging.

Usage:
    python eval/harness.py --n 30 --dry-run     # verify the harness works now
    python eval/harness.py --n 30                # the real thing, once deployed
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from eval.baseline import baseline_would_alert
from eval.scoring import DetectionResult, SeededCondition, render_markdown, score

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eval_conditions.json"
RESULTS_PATH = Path(__file__).parent / "RESULTS.md"

FAULT_TYPES = ["clean", "low_samples", "break_texture", "kill_worker", "starve_memory"]
VISUAL_DEFECT_FAULTS = {"low_samples", "break_texture"}


def generate_seed_plan(n: int, seed: int = 42) -> list[SeededCondition]:
    """Deterministic distribution across failure classes, reproducible with
    the same --seed so results are comparable run over run.
    """
    rng = random.Random(seed)
    conditions = []
    for i in range(n):
        fault = rng.choice(FAULT_TYPES)
        conditions.append(
            SeededCondition(
                condition_id=f"cond-{i:03d}-{fault}",
                fault_type=fault,
                has_visual_defect=fault in VISUAL_DEFECT_FAULTS,
                metrics_would_alert=baseline_would_alert(fault),
            )
        )
    return conditions


def run_dry(conditions: list[SeededCondition]) -> list[DetectionResult]:
    """Scripted stand-in for the real agent, calibrated to the failure modes
    this graph is designed to catch: it flags every visual defect on the
    first pass (the verify loop exists in the real system for cases genuinely
    ambiguous on real footage — this reference run keeps that variable out
    so the harness itself is verifiable independent of live model behavior).
    """
    results = []
    for c in conditions:
        results.append(
            DetectionResult(
                condition_id=c.condition_id,
                agent_flagged=c.has_visual_defect,
                baseline_flagged=c.metrics_would_alert,
            )
        )
    return results


def run_live(conditions: list[SeededCondition], agent_url: str) -> list[DetectionResult]:
    """Dispatch a real backlot render per condition and trigger a real agent
    run against the deployed service, then read back whether it flagged a
    defect. Fill in once the agent service and backlot are both deployed
    (day 9-14 in the plan) — this is intentionally left as the integration
    point rather than guessed at, since it depends on the live server.py
    /runs API and the live job-id/frame-range scheme from backlot/dispatch.py.
    """
    raise NotImplementedError(
        "wire this to backlot/dispatch.py + POST {agent_url}/runs once both "
        "are deployed; until then use --dry-run to exercise the harness/scoring"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent-url", default="http://localhost:8080")
    args = parser.parse_args()

    conditions = generate_seed_plan(args.n, seed=args.seed)
    FIXTURE_PATH.parent.mkdir(exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps([c.__dict__ for c in conditions], indent=2))

    results = run_dry(conditions) if args.dry_run else run_live(conditions, args.agent_url)
    scorecard = score(conditions, results)

    RESULTS_PATH.write_text(render_markdown(scorecard))
    print(render_markdown(scorecard))


if __name__ == "__main__":
    main()
