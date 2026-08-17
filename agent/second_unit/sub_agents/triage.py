"""1. TriageAgent — which render job is most at risk right now?"""
from google.adk.agents import LlmAgent

from second_unit.tools.shotlist import list_active_jobs

MODEL = "gemini-2.5-flash"  # fast triage pass; confirm current model id against
                            # the Gemini Enterprise Agent Platform model list at build time


def _list_jobs_tool() -> list[str]:
    """Return the ids of all render jobs currently tracked on the farm."""
    return list_active_jobs()


triage_agent = LlmAgent(
    name="TriageAgent",
    model=MODEL,
    instruction=(
        "You triage the render farm. Call list_jobs to see every active job. "
        "Pick the single job at highest risk of a missed deadline or wasted spend "
        "— prioritize jobs closest to their due_at, and jobs backing a client "
        "review. Output exactly one job_id and one sentence of reasoning."
    ),
    tools=[_list_jobs_tool],
    output_key="triaged_job_id",
)
