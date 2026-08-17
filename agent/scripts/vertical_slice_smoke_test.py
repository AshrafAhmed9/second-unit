"""Manual smoke test for the full graph: diagnose -> human approval gate ->
actuator write-back, against REAL Grafana MCP and REAL Gemini — no mocks.
This is what proved the day-7 vertical slice end to end (see git history for
the bugs it caught along the way: mcp-grafana PATH resolution, the -tools vs
-enabled-tools CLI flag, TriageAgent needing deterministic ranking instead of
LLM-sorted output, the artifact save/load round trip for EyesAgent's vision,
ReexamineAgent missing its tools entirely, per-runner session isolation, and
a naive/aware datetime mismatch).

Run from second-unit/agent/ with real credentials sourced:
    set -a && source ../.env && set +a && .venv/bin/python scripts/vertical_slice_smoke_test.py

Requires: agent/backlot/frames_local/job-seq042-sh0420/ to contain at least
one rendered frame (see backlot/dispatch.py), and Firestore seeded via
scripts/seed_firestore.py.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from second_unit.agent import act_agent, diagnose_agent

APP_NAME = "second-unit-slice-test"
# Shared across both runners deliberately — an earlier version gave each
# phase its own InMemoryRunner, which silently creates its OWN isolated
# session store. The actuator run then couldn't find the diagnose run's
# session at all (SessionNotFoundError). Real infra bug, also present in
# server.py until fixed there too. Found during the day-7 vertical slice test.
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()


async def main():
    runner = Runner(agent=diagnose_agent, app_name=APP_NAME, session_service=session_service, artifact_service=artifact_service)
    session = await session_service.create_session(app_name=APP_NAME, user_id="tester")

    message = types.Content(role="user", parts=[types.Part.from_text(text="triage and diagnose the highest-risk job now")])

    try:
        async for event in runner.run_async(user_id="tester", session_id=session.id, new_message=message):
            author = getattr(event, "author", "?")
            err = getattr(event, "error_message", None)
            if err:
                print(f"\n!!! ERROR in {author}: {err}")
            text = ""
            if event.content and event.content.parts:
                text = "".join(p.text for p in event.content.parts if p.text)
            if text:
                print(f"\n=== {author} ===\n{text}")
    except* Exception as eg:
        for exc in eg.exceptions:
            print(f"\n!!! EXCEPTION: {type(exc).__name__}: {exc}")

    final = await session_service.get_session(app_name=APP_NAME, user_id="tester", session_id=session.id)
    print("\n\nFINAL STATE KEYS (after diagnose):", list(final.state.keys()))

    print("\n\n========== HUMAN APPROVAL GATE — approving and running ActuatorAgent ==========")
    act_runner = Runner(agent=act_agent, app_name=APP_NAME, session_service=session_service, artifact_service=artifact_service)
    approve_message = types.Content(role="user", parts=[types.Part.from_text(text="approved, execute the plan")])
    try:
        async for event in act_runner.run_async(user_id="tester", session_id=session.id, new_message=approve_message):
            author = getattr(event, "author", "?")
            text = "".join(p.text for p in event.content.parts if p.text) if event.content and event.content.parts else ""
            if text:
                print(f"\n=== {author} ===\n{text}")
    except* Exception as eg:
        for exc in eg.exceptions:
            print(f"\n!!! ACT EXCEPTION: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
