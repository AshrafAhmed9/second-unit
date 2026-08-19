"""FastAPI server fronting the agent graph: streams agent progress over SSE,
exposes the human-approval gate, and serves Demo Mode (a recorded real run,
replayed deterministically, zero API calls, zero cost) as the default state
of the hosted URL — see the plan's "hosted URL must outlive our credits" note.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types
from sse_starlette.sse import EventSourceResponse

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from second_unit.agent import act_agent, diagnose_agent

DEMO_RECORDING_PATH = Path(__file__).parent / "demo_mode" / "recorded_run.json"
APP_NAME = "second-unit"

app = FastAPI(title="SECOND UNIT agent service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the control-room origin before submission
    allow_methods=["*"],
    allow_headers=["*"],
)

_pending_plans: dict[str, dict] = {}

# Shared across both runners deliberately. Each phase used to get its own
# InMemoryRunner, which silently creates its OWN isolated session store —
# the approve step then couldn't find the diagnose step's session at all
# (SessionNotFoundError). Found and fixed during the day-7 vertical slice test.
_session_service = InMemorySessionService()
_artifact_service = InMemoryArtifactService()
_diagnose_runner = Runner(
    agent=diagnose_agent, app_name=APP_NAME, session_service=_session_service, artifact_service=_artifact_service
)
_act_runner = Runner(
    agent=act_agent, app_name=APP_NAME, session_service=_session_service, artifact_service=_artifact_service
)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/demo")
async def demo_mode() -> dict:
    """Replay a real, previously-recorded run. No API calls, no cost, cannot
    break. This is the default landing experience — see control-room/.

    Was typed -> AsyncIterator[dict], which crashed the app at import time:
    FastAPI tries to build a Pydantic response model from the return
    annotation, and AsyncIterator[dict] isn't a valid one — this function
    was never actually a generator, just returns a plain dict. Found via
    Cloud Run's real startup logs after the first deploy attempt failed the
    container health check (it never even got to the Grafana/MCP-related
    code this whole service exists for).
    """
    if not DEMO_RECORDING_PATH.exists():
        raise HTTPException(404, "no demo recording captured yet — see docs/DEMO.md")
    return json.loads(DEMO_RECORDING_PATH.read_text())


@app.post("/runs")
async def start_run(job_id: str | None = None):
    """Kick off the diagnose half of the graph for a given (or auto-triaged) job,
    streamed back over SSE at /runs/{run_id}/events.
    """
    run_id = str(uuid.uuid4())
    await _session_service.create_session(app_name=APP_NAME, user_id="control-room", session_id=run_id)

    prompt = f"diagnose job {job_id}" if job_id else "triage and diagnose the highest-risk job now"
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    async def event_stream() -> AsyncIterator[dict]:
        async for event in _diagnose_runner.run_async(
            user_id="control-room",
            session_id=run_id,
            new_message=message,
        ):
            payload = {"stage": event.author, "content": str(event.content)}
            if event.is_final_response():
                _pending_plans[run_id] = payload
            yield {"event": "stage", "data": json.dumps(payload)}
        yield {"event": "awaiting_approval", "data": json.dumps({"run_id": run_id})}

    return EventSourceResponse(event_stream())


@app.post("/runs/{run_id}/approve")
async def approve_run(run_id: str):
    """The human approval gate. Nothing in act_agent (the Grafana write-back)
    runs before this endpoint is called.
    """
    if run_id not in _pending_plans:
        raise HTTPException(404, "no pending plan for this run_id")

    message = types.Content(role="user", parts=[types.Part.from_text(text="approved, execute the plan")])

    async def event_stream() -> AsyncIterator[dict]:
        async for event in _act_runner.run_async(
            user_id="control-room",
            session_id=run_id,
            new_message=message,
        ):
            yield {"event": "stage", "data": json.dumps({"stage": event.author, "content": str(event.content)})}
        del _pending_plans[run_id]

    return EventSourceResponse(event_stream())


@app.post("/runs/{run_id}/reject")
async def reject_run(run_id: str):
    _pending_plans.pop(run_id, None)
    return {"ok": True}
