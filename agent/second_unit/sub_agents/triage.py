"""1. TriageAgent — which render job is most at risk right now?"""
from google.adk.agents import LlmAgent

from second_unit.tools.shotlist import get_shot_for_job, list_active_jobs

MODEL = "gemini-2.5-flash"  # fast triage pass; confirm current model id against
                            # the Gemini Enterprise Agent Platform model list at build time


def _pick_highest_risk_job_tool() -> dict:
    """Rank every active render job by deadline risk and return the single
    highest-risk one, already sorted — deterministically, in Python, not by
    asking the LLM to reason about sort order. Earlier versions either gave
    the model bare job ids with no risk signal (it correctly refused to
    guess) or gave it raw unsorted data and asked it to rank them itself
    (gemini-2.5-flash responded by writing inline Python sort code instead
    of issuing a real function call, which ADK correctly rejected as a
    malformed call). Both failures point the same direction: risk ranking
    is deterministic arithmetic, so — same principle as schedule.py — it
    belongs in code, not in the model's head. Found during the day-7
    vertical slice test.
    """
    candidates = []
    for job_id in list_active_jobs():
        shot = get_shot_for_job(job_id)
        if shot is None:
            continue
        candidates.append(
            {
                "job_id": job_id,
                "shot_id": shot.shot_id,
                "sequence": shot.sequence,
                "frames_remaining": shot.frames_total - shot.frames_done,
                "due_at": shot.due_at.isoformat(),
                "client_review": shot.client_review,
            }
        )
    if not candidates:
        return {"job_id": None, "reason": "no active jobs"}

    candidates.sort(key=lambda j: (j["due_at"], not j["client_review"], -j["frames_remaining"]))
    winner = candidates[0]
    winner["reason"] = (
        f"closest due_at ({winner['due_at']})"
        + (", backs a client review" if winner["client_review"] else "")
        + f", {winner['frames_remaining']} frames remaining"
    )
    return winner


triage_agent = LlmAgent(
    name="TriageAgent",
    model=MODEL,
    instruction=(
        "Call pick_highest_risk_job — it already ranks every active job by "
        "deadline risk and returns the single highest-risk one. Output MUST "
        "be exactly its job_id value on its own line, with nothing else — no "
        "extra words, no punctuation. You may add the tool's `reason` field "
        "as a second line after that."
    ),
    tools=[_pick_highest_risk_job_tool],
    output_key="triaged_job_id",
)
