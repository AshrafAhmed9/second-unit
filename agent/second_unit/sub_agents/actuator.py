"""7. ActuatorAgent — writes back into Grafana. Runs ONLY after the human
approval gate in agent.py. This is the write-back that most Grafana-track
entries will not attempt: an incident opened, an annotation dropped on the
exact timestamp, and an activity note explaining why — visible natively on
the judge's own Grafana panels, not just on our control room screen.
"""
from google.adk.agents import LlmAgent

from second_unit.tools.grafana_mcp import write_toolset

MODEL = "gemini-2.5-flash"

actuator_agent = LlmAgent(
    name="ActuatorAgent",
    model=MODEL,
    instruction=(
        "A human has approved this plan: {{plan}}, for impact={{impact}} on "
        "job_id={{triaged_job_id}}. Using the Grafana annotation and incident "
        "tools: (1) create an annotation on the relevant dashboard/panel at the "
        "current time, tagged with the job id and shot id, with the impact "
        "headline as the text; (2) open an incident if impact.misses_deadline "
        "is true, titled with the shot id and headline, and add one activity "
        "note summarizing the evidence chain (metrics/logs/traces/visual) that "
        "led here. Report the annotation id and incident id you created."
    ),
    tools=[write_toolset()],
    output_key="actuator_result",
)
