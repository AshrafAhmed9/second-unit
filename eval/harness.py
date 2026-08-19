"""THE PROOF — run seeded conditions across the failure classes, score the
agent against a threshold-alerting baseline, and commit a regenerable
scorecard to eval/RESULTS.md. No sampled past hackathon winner shipped this;
it is the cheapest available edge over the rest of the field.

Two modes:
  --dry-run    Uses a synthetic n-condition plan + a scripted "agent" so the
               harness and scoring logic are testable with no live
               Grafana/Gemini dependency. This is what CI runs.
  (default)    Scores exactly what's actually been rendered by
               backlot/render_eval_conditions.py (backlot/eval_job_map.json),
               running the REAL evidence+verify agent graph in-process
               against REAL Gemini + REAL Grafana MCP for each real job. The
               condition count here is however many real frames exist, not
               an arbitrary --n — inflating that number without real renders
               behind it would be exactly the synthetic-data problem this
               project's whole design argues against.

Usage:
    python eval/harness.py --dry-run              # verify the harness works, no live deps
    python eval/harness.py                          # score the real rendered batch
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from eval.baseline import baseline_would_alert
from eval.scoring import DetectionResult, SeededCondition, render_markdown, score

RESULTS_PATH = Path(__file__).parent / "RESULTS.md"
JOB_MAP_PATH = Path(__file__).resolve().parent.parent / "backlot" / "eval_job_map.json"

FAULT_TYPES = ["clean", "low_samples", "break_texture", "kill_worker", "starve_memory"]
VISUAL_DEFECT_FAULTS = {"low_samples", "break_texture"}

# Loose keyword classifier over the agent's own free-text visual_evidence.
# A real limitation, stated plainly: this is not a structured/schema'd
# verdict, so it's a heuristic over natural language, not a guaranteed-exact
# parse. Documented here rather than hidden — see README "Path to production"
# for the honest path to a stricter version (e.g. an output_schema on
# EyesAgent/ReexamineAgent instead of a free-text field).
#
# Detects DEFECT language directly rather than inferring a defect from the
# absence of "clean" phrases. The absence-based version scored a real,
# correct detection ("I have found visual artifacts... noticeable noise") as
# NOT flagged, because the model's phrasing didn't happen to match any of
# the specific "clean" strings being checked for — defect vocabulary is far
# more consistent across responses than cleanliness vocabulary is. Found
# scoring the first eval run after the loop-exit fix.
_DEFECT_PHRASES = (
    "defect", "artifact", "firefl", "noise", "noisy", "grain", "speckle",
    "corrupt", "missing texture", "black frame", "blank frame", "pink texture",
)


def classify_visual_evidence(text: str) -> bool:
    """Return True if the agent's final visual_evidence claims a defect."""
    lowered = text.lower()
    return any(phrase in lowered for phrase in _DEFECT_PHRASES)


def generate_seed_plan(n: int, seed: int = 42) -> list[SeededCondition]:
    """Synthetic distribution across failure classes for --dry-run only."""
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
    """Scripted stand-in for the real agent — see module docstring."""
    return [
        DetectionResult(condition_id=c.condition_id, agent_flagged=c.has_visual_defect, baseline_flagged=c.metrics_would_alert)
        for c in conditions
    ]


def load_real_conditions() -> list[SeededCondition]:
    """Build the real condition list from backlot/eval_job_map.json — the
    ground truth is the condition each job was ACTUALLY rendered under (see
    backlot/render_eval_conditions.py), not an assumption.
    """
    if not JOB_MAP_PATH.exists():
        raise FileNotFoundError(
            f"{JOB_MAP_PATH} not found. Run `python backlot/render_eval_conditions.py` first "
            "to produce real rendered frames to score."
        )
    job_map: dict[str, str] = json.loads(JOB_MAP_PATH.read_text())
    return [
        SeededCondition(
            condition_id=job_id,
            fault_type=fault,
            has_visual_defect=fault in VISUAL_DEFECT_FAULTS,
            metrics_would_alert=baseline_would_alert(fault),
        )
        for job_id, fault in job_map.items()
    ]


async def _run_one_condition(condition: SeededCondition) -> DetectionResult:
    """Run the REAL evidence+verify sub-graph (not the full diagnose graph —
    triage/impact/plan/actuator aren't part of the detection question this
    harness is scoring) against one real rendered job, in-process, against
    real Gemini and real Grafana MCP.
    """
    from google.adk.agents import SequentialAgent
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from second_unit.sub_agents.evidence import build_evidence_agents
    from second_unit.sub_agents.verify import build_verify_loop

    detect_agent = SequentialAgent(name="EvalDetect", sub_agents=[build_evidence_agents(), build_verify_loop()])
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    runner = Runner(
        agent=detect_agent, app_name="second-unit-eval", session_service=session_service, artifact_service=artifact_service
    )
    session = await session_service.create_session(
        app_name="second-unit-eval", user_id="eval", state={"triaged_job_id": condition.condition_id}
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text="check this job")])

    async for _ in runner.run_async(user_id="eval", session_id=session.id, new_message=message):
        pass

    final = await session_service.get_session(app_name="second-unit-eval", user_id="eval", session_id=session.id)
    visual_evidence = final.state.get("visual_evidence", "")
    agent_flagged = classify_visual_evidence(visual_evidence) if visual_evidence else False
    print(f"    [{condition.condition_id}] flagged={agent_flagged} | visual_evidence: {visual_evidence[:200]!r}")

    return DetectionResult(
        condition_id=condition.condition_id,
        agent_flagged=agent_flagged,
        baseline_flagged=condition.metrics_would_alert,
    )


async def _run_one_condition_with_retry(condition: SeededCondition, max_attempts: int = 4) -> DetectionResult:
    """Retry with exponential backoff on Vertex AI 429 RESOURCE_EXHAUSTED —
    a fresh GCP project's default generate_content quota is low enough that
    running evidence_agents' 4 parallel Gemini calls back to back across 8
    conditions genuinely exhausts it. Not a code bug, but the harness should
    survive it rather than die on condition 4 of 8 (which is what happened
    on the first live run after the loop-exit fix).
    """
    from google.genai.errors import ClientError

    for attempt in range(1, max_attempts + 1):
        try:
            return await _run_one_condition(condition)
        except ClientError as e:
            if getattr(e, "code", None) != 429 or attempt == max_attempts:
                raise
            backoff_s = 20 * attempt
            print(f"    [{condition.condition_id}] 429 rate-limited, retrying in {backoff_s}s (attempt {attempt}/{max_attempts})...")
            await asyncio.sleep(backoff_s)
    raise RuntimeError("unreachable")


def run_live(conditions: list[SeededCondition]) -> list[DetectionResult]:
    async def _run_all():
        results = []
        for i, c in enumerate(conditions):
            print(f"  scoring {c.condition_id} (real condition: {c.fault_type})...")
            results.append(await _run_one_condition_with_retry(c))
            if i < len(conditions) - 1:
                await asyncio.sleep(10)  # cooldown between conditions, same quota reason as above
        return results

    return asyncio.run(_run_all())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30, help="dry-run only: synthetic condition count")
    parser.add_argument("--seed", type=int, default=42, help="dry-run only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        conditions = generate_seed_plan(args.n, seed=args.seed)
        results = run_dry(conditions)
    else:
        conditions = load_real_conditions()
        print(f"scoring {len(conditions)} REAL rendered conditions against the real agent...")
        results = run_live(conditions)

    scorecard = score(conditions, results)
    RESULTS_PATH.write_text(render_markdown(scorecard))
    print(render_markdown(scorecard))


if __name__ == "__main__":
    main()
