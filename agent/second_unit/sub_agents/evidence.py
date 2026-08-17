"""2. ParallelAgent "evidence" — four agents gathering evidence on the triaged job.

Three ask "is the infra healthy?" via Grafana MCP. One — EyesAgent, the whole
point of this project — asks "is the PICTURE ok?" via Gemini vision, which is
the question no observability tool can answer.
"""
from google.adk.agents import LlmAgent, ParallelAgent

from second_unit.tools.frames import list_frames
from second_unit.tools.grafana_mcp import read_toolset

# NOTE: ADK's function-tool return value is text/JSON, not multimodal. Getting
# actual image bytes in front of EyesAgent needs one of: (a) an ADK tool that
# returns Part objects directly if the installed ADK version supports it, or
# (b) a thin wrapper that loads frames via as_gemini_image_parts() and injects
# them into the session before this agent runs. Resolve this concretely during
# the day-7 vertical slice — it is the single most important call in the graph.

MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-pro"  # vision quality matters most here; confirm current id at build time

metrics_agent = LlmAgent(
    name="MetricsAgent",
    model=MODEL,
    instruction=(
        "Given job_id={{triaged_job_id}}, use the Prometheus tools (via Grafana MCP) "
        "to check GPU utilization, queue depth, and node churn for this job's worker "
        "pool over the last 30 minutes. Report whether metrics are green, and any anomaly."
    ),
    tools=[read_toolset()],
    output_key="metrics_evidence",
)

logs_agent = LlmAgent(
    name="LogsAgent",
    model=MODEL,
    instruction=(
        "Given job_id={{triaged_job_id}}, use the Loki tools (via Grafana MCP) to "
        "search renderer stderr/stdout for this job for retry storms, OOM kills, "
        "or asset errors in the last 30 minutes. Report what you find, or 'clean'."
    ),
    tools=[read_toolset()],
    output_key="logs_evidence",
)

trace_agent = LlmAgent(
    name="TraceAgent",
    model=MODEL,
    instruction=(
        "Given job_id={{triaged_job_id}}, use the Tempo tools (via Grafana MCP) to "
        "inspect per-frame render spans for this job. Report unusually long spans, "
        "orphaned/retried spans, or 'clean'."
    ),
    tools=[read_toolset()],
    output_key="trace_evidence",
)


def _load_frames_tool(job_id: str) -> list[str]:
    """Return image references for the most recently rendered frames of a job."""
    return list_frames(job_id)[-8:]


eyes_agent = LlmAgent(
    name="EyesAgent",
    model=VISION_MODEL,
    instruction=(
        "Given job_id={{triaged_job_id}}, call load_frames to get the most recent "
        "rendered frames, then actually look at them. Metrics and logs can say a "
        "render 'succeeded' — your job is to check whether the PICTURE is correct: "
        "denoiser fireflies/noise, black or blank frames, missing/pink textures, "
        "obviously corrupted geometry. This is the one check nothing else on the "
        "farm can perform. Name the specific frame(s) and defect if you see one, "
        "otherwise say the frames look clean. Be concrete, not vague."
    ),
    tools=[_load_frames_tool],
    output_key="visual_evidence",
)

evidence_agents = ParallelAgent(
    name="EvidenceAgent",
    sub_agents=[metrics_agent, logs_agent, trace_agent, eyes_agent],
)
