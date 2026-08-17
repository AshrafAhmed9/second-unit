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
from sse_starlette.sse import EventSourceResponse

from google.adk.runners import InMemoryRunner

from second_unit.agent import act_agent, diagnose_agent

DEMO_RECORDING_PATH = Path(__file__).parent / "demo_mode" / "recorded_run.json"

app = FastAPI(title="SECOND UNIT agent service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the control-room origin before submission
    allow_methods=["*"],
    allow_headers=["*"],
)

_pending_plans: dict[str, dict] = {}
_diagnose_runner = InMemoryRunner(agent=diagnose_agent, app_name="second-unit")
_act_runner = InMemoryRunner(agent=act_agent, app_name="second-unit")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/demo")
async def demo_mode() -> AsyncIterator[dict]:
    """Replay a real, previously-recorded run. No API calls, no cost, cannot
    break. This is the default landing experience — see control-room/.
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

    async def event_stream() -> AsyncIterator[dict]:
        async for event in _diagnose_runner.run_async(
            user_id="control-room",
            session_id=run_id,
            new_message=job_id or "triage and diagnose the highest-risk job now",
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

    async def event_stream() -> AsyncIterator[dict]:
        async for event in _act_runner.run_async(
            user_id="control-room",
            session_id=run_id,
            new_message="execute the approved plan",
        ):
            yield {"event": "stage", "data": json.dumps({"stage": event.author, "content": str(event.content)})}
        del _pending_plans[run_id]

    return EventSourceResponse(event_stream())


@app.post("/runs/{run_id}/reject")
async def reject_run(run_id: str):
    _pending_plans.pop(run_id, None)
    return {"ok": True}
