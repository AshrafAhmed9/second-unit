"""Runs the real EyesAgent -> VerdictAgent path against one clean render and
one defective render, recording both verdicts verbatim to
agent/demo_mode/frame_proof.json. Two Gemini calls, meant to be run once and
committed — the control room's VisionProof panel imports the result at
build time so it renders even with the agent service asleep.

Usage:
    python agent/scripts/capture_frame_proof.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "agent"))

OUTPUT_PATH = REPO_ROOT / "agent" / "demo_mode" / "frame_proof.json"

PAIRS = [
    {"condition_id": "eval-clean-000", "label": "clean", "frame": "eval-clean-000__frame_0001.png"},
    {"condition_id": "eval-low_samples-003", "label": "defective", "frame": "eval-low_samples-003__frame_0001.png"},
]


async def _run_one(condition_id: str) -> dict:
    from google.adk.agents import SequentialAgent
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from second_unit.sub_agents.evidence import build_evidence_agents
    from second_unit.sub_agents.verdict import build_verdict_agent

    # EyesAgent only (via evidence_agents' ParallelAgent) -> VerdictAgent —
    # not the full evidence set, since this is proving the vision->verdict
    # link specifically, the same pair eval/harness.py scores.
    detect_agent = SequentialAgent(name="FrameProof", sub_agents=[build_evidence_agents(), build_verdict_agent()])

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    runner = Runner(agent=detect_agent, app_name="second-unit-frame-proof", session_service=session_service, artifact_service=artifact_service)
    session = await session_service.create_session(app_name="second-unit-frame-proof", user_id="proof", state={"triaged_job_id": condition_id})
    message = types.Content(role="user", parts=[types.Part.from_text(text="check this job")])

    async for _ in runner.run_async(user_id="proof", session_id=session.id, new_message=message):
        pass

    final = await session_service.get_session(app_name="second-unit-frame-proof", user_id="proof", session_id=session.id)
    verdict = final.state.get("visual_verdict")
    visual_evidence = final.state.get("visual_evidence")
    has_defect = verdict["has_defect"] if isinstance(verdict, dict) else verdict.has_defect
    reasoning = verdict["reasoning"] if isinstance(verdict, dict) else verdict.reasoning
    return {"has_defect": has_defect, "reasoning": reasoning, "visual_evidence": visual_evidence}


async def main() -> None:
    results = []
    for pair in PAIRS:
        print(f"scoring {pair['condition_id']}...")
        verdict = await _run_one(pair["condition_id"])
        results.append({**pair, **verdict})
        print(f"  has_defect={verdict['has_defect']} | {verdict['reasoning']}")

    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
