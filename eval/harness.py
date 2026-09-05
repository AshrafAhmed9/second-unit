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

REPO_ROOT = Path(__file__).resolve().parent.parent
# Both needed, for a real reason: running `python eval/harness.py` directly
# (as the README's quickstart does) puts eval/'s OWN directory on
# sys.path[0], not its parent — so `from eval.baseline import ...` below
# can't resolve `eval` as a package without the repo root also on the path.
# Found by literally running the README's documented command as written —
# it failed with ModuleNotFoundError: No module named 'eval'.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "agent"))

from eval.baseline import baseline_would_alert
from eval.scoring import DetectionResult, SeededCondition, render_markdown, score

RESULTS_PATH = Path(__file__).parent / "RESULTS.md"
DRY_RUN_RESULTS_PATH = Path(__file__).parent / "RESULTS.dry-run.md"
JOB_MAP_PATH = Path(__file__).resolve().parent.parent / "backlot" / "eval_job_map.json"

FAULT_TYPES = ["clean", "low_samples", "break_texture", "kill_worker", "starve_memory"]
VISUAL_DEFECT_FAULTS = {"low_samples", "break_texture"}

# Classification used to be a keyword heuristic directly over
# visual_evidence text. Two versions were tried and both failed in opposite,
# embarrassing ways: an absence-of-"clean"-phrases version scored a real
# detection ("I have found visual artifacts... noise") as not flagged
# because its exact wording didn't match; a presence-of-defect-words version
# then scored a real negation ("There are no visual defects... clean") as
# flagged, because "defect" matched regardless of the "no" in front of it.
# That's not a tuning problem — prose parsing was the wrong tool for a
# question with a real structured answer. Replaced with VerdictAgent
# (second_unit/sub_agents/verdict.py), a small no-tools agent using ADK's
# output_schema to produce an actual has_defect: bool. See that file's
# docstring for why it's a separate agent rather than output_schema bolted
# onto EyesAgent/ReexamineAgent directly.


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


def _find_mcp_toolsets(agent) -> list:
    """Walk an agent tree and collect every MCPToolset instance so it can be
    explicitly closed. Each evidence agent's tools=[read_toolset()] spins up
    its own `mcp-grafana` subprocess (grafana_mcp.py), and nothing in ADK
    closes it automatically when the agent/session goes out of scope.
    Building fresh agents per condition (required — see build_evidence_agents'
    docstring, an ADK agent can only have one parent) without closing these
    leaked 3 new subprocesses per condition. Across an 11-condition real run
    that piled up 30+ orphaned subprocesses and eventually hung the harness
    for hours — found by running the real 11-condition eval after the OTLP
    telemetry fix and watching it stall with a live TCP connection but zero
    CPU progress; `ps` on the child processes showed the pile-up.
    """
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

    toolsets = []
    for sub in getattr(agent, "sub_agents", []) or []:
        toolsets.extend(_find_mcp_toolsets(sub))
    for tool in getattr(agent, "tools", []) or []:
        if isinstance(tool, MCPToolset):
            toolsets.append(tool)
    return toolsets


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
    from second_unit.sub_agents.verdict import build_verdict_agent
    from second_unit.sub_agents.verify import build_verify_loop

    detect_agent = SequentialAgent(
        name="EvalDetect",
        sub_agents=[build_evidence_agents(), build_verify_loop(), build_verdict_agent()],
    )
    mcp_toolsets = _find_mcp_toolsets(detect_agent)
    try:
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
        verdict = final.state.get("visual_verdict")
        if verdict is None:
            raise RuntimeError(f"VerdictAgent produced no output for {condition.condition_id}")
        agent_flagged = verdict["has_defect"] if isinstance(verdict, dict) else verdict.has_defect
        reasoning = verdict["reasoning"] if isinstance(verdict, dict) else verdict.reasoning
        print(f"    [{condition.condition_id}] has_defect={agent_flagged} | {reasoning}")

        return DetectionResult(
            condition_id=condition.condition_id,
            agent_flagged=agent_flagged,
            baseline_flagged=condition.metrics_would_alert,
        )
    finally:
        for toolset in mcp_toolsets:
            await toolset.close()


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
        # Deliberately NOT eval/RESULTS.md — that file is the real, committed
        # scorecard judges see. A dry run sharing its output path would
        # silently overwrite real results with synthetic ones; this actually
        # happened once, testing the README's own quickstart command.
        output_path = DRY_RUN_RESULTS_PATH
    else:
        conditions = load_real_conditions()
        print(f"scoring {len(conditions)} REAL rendered conditions against the real agent...")
        results = run_live(conditions)
        output_path = RESULTS_PATH

    scorecard = score(conditions, results)
    output_path.write_text(render_markdown(scorecard))
    print(render_markdown(scorecard))


if __name__ == "__main__":
    main()
