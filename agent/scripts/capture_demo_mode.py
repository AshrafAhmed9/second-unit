"""Capture a REAL run of the full graph (diagnose -> human approval ->
actuator write-back) into agent/demo_mode/recorded_run.json, replacing the
placeholder. This is what the hosted control room's Demo Mode serves by
default — a real recorded run, replayed with zero live API calls, so the
hosted URL keeps working for a judge even after credits eventually lapse.

Prerequisite: fixtures/shotlist.json's job (job-seq042-sh0420) must have a
real rendered frame — with a real defect — sitting in
backlot/frames_local/job-seq042-sh0420/. Point that at one of the real
low_samples frames from backlot/render_eval_conditions.py before running
this (see the copy step this script performs below).

Run from second-unit/agent/ with real credentials sourced:
    set -a && source ../.env && set +a && .venv/bin/python scripts/capture_demo_mode.py
"""
import asyncio
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from second_unit.agent import act_agent, diagnose_agent

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DEFECT_FRAME = REPO_ROOT / "backlot" / "frames_local" / "eval-low_samples-003" / "frame_0001.png"
TARGET_JOB_DIR = REPO_ROOT / "backlot" / "frames_local" / "job-seq042-sh0420"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "demo_mode" / "recorded_run.json"

APP_NAME = "second-unit-demo-capture"


def _stage_text(event) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(p.text for p in event.content.parts if p.text)


async def main():
    if not SOURCE_DEFECT_FRAME.exists():
        raise FileNotFoundError(
            f"{SOURCE_DEFECT_FRAME} missing — run backlot/render_eval_conditions.py first"
        )
    TARGET_JOB_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE_DEFECT_FRAME, TARGET_JOB_DIR / "frame_0181.png")
    print(f"copied real defect frame -> {TARGET_JOB_DIR}")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    diagnose_runner = Runner(
        agent=diagnose_agent, app_name=APP_NAME, session_service=session_service, artifact_service=artifact_service
    )
    session = await session_service.create_session(app_name=APP_NAME, user_id="demo")
    message = types.Content(role="user", parts=[types.Part.from_text(text="triage and diagnose the highest-risk job now")])

    stages = []
    async for event in diagnose_runner.run_async(user_id="demo", session_id=session.id, new_message=message):
        text = _stage_text(event)
        if text:
            stages.append({"stage": event.author, "content": text})
            print(f"  [{event.author}] {text[:100]}")

    diag_state = (await session_service.get_session(app_name=APP_NAME, user_id="demo", session_id=session.id)).state
    # TriageAgent's instruction allows a reasoning line after the bare job_id
    # ("job-seq042-sh0420\nclosest due_at ..."); take only the first line.
    # Found in the first real capture: the full multi-line text ended up in
    # the recording's job_id field verbatim.
    job_id = diag_state.get("triaged_job_id", "job-seq042-sh0420").strip().splitlines()[0].strip()

    print("\n--- human approval gate ---")
    act_runner = Runner(agent=act_agent, app_name=APP_NAME, session_service=session_service, artifact_service=artifact_service)
    approve_message = types.Content(role="user", parts=[types.Part.from_text(text="approved, execute the plan")])
    async for event in act_runner.run_async(user_id="demo", session_id=session.id, new_message=approve_message):
        text = _stage_text(event)
        if text:
            stages.append({"stage": event.author, "content": text})
            print(f"  [{event.author}] {text[:100]}")

    final_state = (await session_service.get_session(app_name=APP_NAME, user_id="demo", session_id=session.id)).state

    results_md = (REPO_ROOT / "eval" / "RESULTS.md").read_text()
    import re
    def pct(label):
        m = re.search(rf"{label}.*?(\d+)%", results_md)
        return int(m.group(1)) / 100 if m else 0.0
    def count(label):
        m = re.search(rf"{label}.*?\*\*(\d+)\*\*", results_md)
        return int(m.group(1)) if m else 0

    recording = {
        "job_id": job_id,
        "shot_id": "sh0420",
        "sequence": "seq042",
        "due_at": "2026-08-18T09:00:00Z",
        "stages": stages,
        "impact_headline": final_state.get("impact", {}).get("headline", "") if isinstance(final_state.get("impact"), dict) else str(final_state.get("impact", "")),
        "plan": final_state.get("plan", ""),
        "actuator_result": final_state.get("actuator_result", ""),
        "scorecard": {
            "detection_rate": pct("Agent detection rate"),
            "false_positive_rate": pct("Agent false positive rate"),
            "baseline_detection_rate": pct(r"Baseline.*?detection rate"),
            "vision_only_catches": count(r"Defects the baseline missed"),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(recording, indent=2))
    print(f"\nwrote real recorded run -> {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
