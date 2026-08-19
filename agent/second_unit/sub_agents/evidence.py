"""2. ParallelAgent "evidence" — four agents gathering evidence on the triaged job.

Three ask "is the infra healthy?" via Grafana MCP. One — EyesAgent, the whole
point of this project — asks "is the PICTURE ok?" via Gemini vision, which is
the question no observability tool can answer.
"""
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import ToolContext
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.genai import types

from second_unit.tools.frames import list_frames, load_frame_bytes
from second_unit.tools.grafana_mcp import read_toolset

MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-pro"  # vision quality matters most here; confirm current id at build time

# Every MCP time-range tool accepts relative strings like "now" and "now-30m"
# directly (see mcp-grafana's own tool schemas). Said explicitly in every
# instruction below because gemini-2.5-flash otherwise sometimes tries to
# compute an actual timestamp via inline Python (`datetime.now(timezone.utc)`)
# instead of issuing a real function call, which ADK correctly rejects as a
# malformed call — the same failure mode hit and fixed in TriageAgent's
# ranking logic. Found during the day-7 vertical slice test.
_TIME_RANGE_NOTE = (
    " For any time range, pass the literal strings \"now-30m\" and \"now\" as "
    "arguments — do not compute or construct timestamps yourself."
)


async def _load_frames_tool(job_id: str, tool_context: ToolContext) -> dict:
    """Fetch the most recent rendered frames for a job and save each one as a
    session artifact, returning their artifact names. This is the actual
    mechanism for getting pixel data in front of a vision-capable ADK agent:
    a plain function-tool return value is text/JSON only, so the real image
    bytes have to go through ToolContext.save_artifact() and then be pulled
    back into context via ADK's built-in `load_artifacts` tool (see
    load_artifacts_tool below) — that second call is what actually inlines
    the image Parts into the model's next turn.
    """
    frame_refs = list_frames(job_id)[-8:]
    artifact_names = []
    for ref in frame_refs:
        data = load_frame_bytes(ref)
        name = ref.rsplit("/", 1)[-1]
        await tool_context.save_artifact(name, types.Part.from_bytes(data=data, mime_type="image/png"))
        artifact_names.append(name)
    return {
        "artifact_names": artifact_names,
        "instruction": "call load_artifacts with these artifact_names to actually see the frames",
    }


def build_evidence_agents() -> ParallelAgent:
    """Factory, not a singleton — an ADK agent can only ever have one parent,
    so anything that needs to run the evidence step more than once per
    process (e.g. eval/harness.py scoring multiple conditions in a loop)
    must build fresh agent instances each time, not reuse module-level
    objects. Found during the first real eval harness run: reusing the
    shared singletons crashed on the second scored condition with
    "Agent `EvidenceAgent` already has a parent agent". The production
    graph (agent.py) still gets one singleton, built by calling this once
    below — nothing changes for it.
    """
    metrics_agent = LlmAgent(
        name="MetricsAgent",
        model=MODEL,
        instruction=(
            "Given job_id={{triaged_job_id}}, use the Prometheus tools (via Grafana MCP) "
            "to check GPU utilization, queue depth, and node churn for this job's worker "
            "pool over the last 30 minutes." + _TIME_RANGE_NOTE +
            " Report whether metrics are green, and any anomaly."
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
            "or asset errors in the last 30 minutes." + _TIME_RANGE_NOTE +
            " Report what you find, or 'clean'."
        ),
        tools=[read_toolset()],
        output_key="logs_evidence",
    )

    trace_agent = LlmAgent(
        name="TraceAgent",
        model=MODEL,
        instruction=(
            "Given job_id={{triaged_job_id}}, use the Tempo tools (via Grafana MCP) to "
            "inspect per-frame render spans for this job over the last 30 minutes." + _TIME_RANGE_NOTE +
            " Report unusually long spans, orphaned/retried spans, or 'clean'."
        ),
        tools=[read_toolset()],
        output_key="trace_evidence",
    )

    eyes_agent = LlmAgent(
        name="EyesAgent",
        model=VISION_MODEL,
        instruction=(
            "Given job_id={{triaged_job_id}}: (1) call load_frames to fetch the most "
            "recent rendered frames as artifacts, (2) call load_artifacts with the "
            "artifact_names it returns to actually load the pixel data into view, "
            "then (3) look at them. Metrics and logs can say a render 'succeeded' — "
            "your job is to check whether the PICTURE is correct: denoiser "
            "fireflies/noise, black or blank frames, missing/pink textures, obviously "
            "corrupted geometry. This is the one check nothing else on the farm can "
            "perform. Name the specific frame(s) and defect if you see one, otherwise "
            "say the frames look clean. Be concrete, not vague — describe what you "
            "actually see, not what you'd expect to see."
        ),
        tools=[_load_frames_tool, load_artifacts_tool],
        output_key="visual_evidence",
    )

    return ParallelAgent(
        name="EvidenceAgent",
        sub_agents=[metrics_agent, logs_agent, trace_agent, eyes_agent],
    )


evidence_agents = build_evidence_agents()
