"""7. ActuatorAgent — writes back into Grafana. Runs ONLY after the human
approval gate in agent.py. This is the write-back that most Grafana-track
entries will not attempt: an annotation dropped on the exact timestamp
(and, where available, an incident with an activity note) — visible
natively on the judge's own Grafana panels, not just on our control room
screen.

Annotations are the required write-back; incidents are best effort. Real
finding: creating an incident on this stack fails inside Grafana's own
backend (`Counters_orgID_fk` foreign key error) because Grafana IRM isn't
provisioned for the org, and there's no API to provision it. Annotations
have worked every time (verified: real annotation IDs created on a real
stack). Rather than let a raw MySQL error leak into the demo output — which
is exactly what the first real Demo Mode capture recorded — the agent is
told to report a clean one-line explanation instead. A production system
would degrade the same way.
"""
from google.adk.agents import LlmAgent

from second_unit.tools.grafana_mcp import write_toolset

MODEL = "gemini-2.5-flash"

actuator_agent = LlmAgent(
    name="ActuatorAgent",
    model=MODEL,
    # include_contents='none': ActuatorAgent must act ONLY on the templated
    # state below, never on the full prior conversation. With the default
    # ('default'), diagnose and act share one session (correctly, so state
    # persists across the human approval gate) — but that also means this
    # agent would otherwise see every evidence agent's back-and-forth,
    # including unresolved investigative threads (e.g. MetricsAgent retrying
    # a failed query). Observed once: given a generic "approved, execute"
    # message, the model picked up MetricsAgent's unfinished Prometheus
    # investigation instead of doing its own job, and called a tool it
    # doesn't have. Found during the day-7 vertical slice test.
    include_contents="none",
    instruction=(
        "A human has approved this plan: {{plan}}, for impact={{impact}} on "
        "job_id={{triaged_job_id}}.\n"
        "STEP 1 (required): create an annotation tagged with the job id and "
        "shot id, with the impact headline as the text. This is the primary "
        "write-back and it must succeed.\n"
        "STEP 2 (best effort): if impact.misses_deadline is true, also try to "
        "open an incident titled with the shot id and headline, and add one "
        "activity note summarizing the evidence chain that led here.\n"
        "Report the annotation id you created. If the incident tool returns an "
        "error, do NOT paste the raw error text — Grafana IRM is simply not "
        "provisioned on every stack, which is expected and not a failure of "
        "this run. Just say: 'Incident not created (Grafana IRM unavailable on "
        "this stack); annotation is the system of record.' Do not attempt any "
        "tool outside annotations/incidents — you do not have metrics, logs, or "
        "trace access, and should not need it."
    ),
    tools=[write_toolset()],
    output_key="actuator_result",
)
