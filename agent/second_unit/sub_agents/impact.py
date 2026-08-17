"""4. ImpactAgent — telemetry translated into schedule and money.

The arithmetic itself is NOT done by the LLM (see second_unit/schedule.py —
pure, unit-tested functions). The agent's only job is to read the evidence,
decide how many frames are actually affected, and call the calculator.
"""
from datetime import datetime, timezone

from google.adk.agents import LlmAgent

from second_unit.schedule import compute_impact
from second_unit.tools.shotlist import get_shot_for_job

MODEL = "gemini-2.5-flash"


def _compute_impact_tool(job_id: str, wasted_frames: int) -> dict:
    """Compute the deadline/cost impact of `wasted_frames` needing re-render on
    the shot behind `job_id`. Returns the headline sentence and the numbers
    behind it (wasted_gpu_hours, wasted_cost_usd, delay_hours, misses_deadline,
    overtime_cost_usd) so the answer is auditable, not asserted.
    """
    shot = get_shot_for_job(job_id)
    if shot is None:
        return {"error": f"no shot found for job_id={job_id}"}
    impact = compute_impact(shot, wasted_frames, now=datetime.now(timezone.utc))
    return impact.__dict__


impact_agent = LlmAgent(
    name="ImpactAgent",
    model=MODEL,
    instruction=(
        "You have evidence for job_id={{triaged_job_id}}: "
        "metrics={{metrics_evidence}} logs={{logs_evidence}} traces={{trace_evidence}} "
        "visual={{visual_evidence}}. If the visual evidence names specific defective "
        "frames, estimate how many frames must be re-rendered (a reasonable count "
        "from what was named — do not invent a large number). Call compute_impact "
        "with that count. If there is no confirmed defect, call compute_impact with "
        "wasted_frames=0. Report the resulting headline verbatim."
    ),
    tools=[_compute_impact_tool],
    output_key="impact",
)
