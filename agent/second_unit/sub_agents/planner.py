"""5. PlannerAgent — propose a remediation, with rationale, for a human to approve."""
from google.adk.agents import LlmAgent

MODEL = "gemini-2.5-flash"

planner_agent = LlmAgent(
    name="PlannerAgent",
    model=MODEL,
    instruction=(
        "Given impact={{impact}} and the underlying evidence (metrics, logs, "
        "traces, visual), propose ONE concrete remediation: e.g. 're-render "
        "frames 1180-1194 on a clean node', 'roll back texture path to last-known-"
        "good and re-render', 'no action — false alarm'. State your reasoning in "
        "two sentences max. This proposal will be shown to a human for approval "
        "before anything runs — do not claim to have already acted."
    ),
    output_key="plan",
)
