"""Quick isolated check: does VerdictAgent's structured output actually work
and read the negation correctly, before spending a full eval harness run on it.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from second_unit.sub_agents.verdict import build_verdict_agent

CASES = {
    "clean-negated": "There are no visual defects in frame_0001.png. The frame is clean.",
    "real-defect": "The frame shows significant noise and grain, a classic denoiser artifact.",
    "compression-mention": "The image is PNG, a lossless format, so no compression artifacts exist. The cube renders correctly.",
}


async def main():
    for label, text in CASES.items():
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        agent = build_verdict_agent()
        runner = Runner(agent=agent, app_name="smoke", session_service=session_service, artifact_service=artifact_service)
        session = await session_service.create_session(app_name="smoke", user_id="t", state={"visual_evidence": text})
        message = types.Content(role="user", parts=[types.Part.from_text(text="classify")])
        async for _ in runner.run_async(user_id="t", session_id=session.id, new_message=message):
            pass
        final = await session_service.get_session(app_name="smoke", user_id="t", session_id=session.id)
        v = final.state.get("visual_verdict")
        print(f"{label}: has_defect={v.get('has_defect') if isinstance(v, dict) else v} | input={text[:60]!r}")


if __name__ == "__main__":
    asyncio.run(main())
