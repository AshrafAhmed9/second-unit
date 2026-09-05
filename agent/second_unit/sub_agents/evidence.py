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

# Prometheus's and Loki's MCP time-range tools accept relative strings like
# "now" and "now-30m" directly. Said explicitly because gemini-2.5-flash
# otherwise sometimes tries to compute an actual timestamp via inline Python
# (`datetime.now(timezone.utc)`) instead of issuing a real function call,
# which ADK correctly rejects as a malformed call — the same failure mode hit
# and fixed in TriageAgent's ranking logic. Found during the day-7 vertical
# slice test.
_TIME_RANGE_NOTE = (
    " For any time range, pass the literal strings \"now-30m\" and \"now\" as "
    "arguments — do not compute or construct timestamps yourself."
)

# Tempo's tempo_traceql_search tool is different: its start/end parameters are
# documented to accept ONLY RFC3339 timestamps and reject "now-30m"/"now"
# outright ("cannot parse \"now-30m\" as \"2006\""). Reusing _TIME_RANGE_NOTE
# here made TraceAgent hit that error, then — obeying the "do not construct
# timestamps yourself" instruction literally — refuse to retry and ask the
# user a clarifying question instead of ever reporting real trace evidence.
# Found via adversarial review of the recorded demo, where this was baked in
# as TraceAgent's entire "finding."
#
# The first fix attempt told the model to "compute start as (now - 30
# minutes)" — gemini-2.5-flash took that as license to write actual inline
# Python (`from datetime import datetime...`) as its "function call," which
# ADK correctly rejects as MALFORMED_FUNCTION_CALL, so TraceAgent's final
# turn had a tool error and no text at all (empty trace_evidence). Found via
# a real capture_demo_mode.py run after the OTLP fix, isolating TraceAgent
# alone. The actual fix: never ask the model to compute anything — Python
# computes the real RFC3339 window and bakes literal values into the
# instruction text, the same pattern as the Prometheus/Loki "now-30m"
# literal. instruction= is a callable here (not a fixed string) so the
# window is always current, not frozen at process start.
def _tempo_instruction(ctx) -> str:
    """ADK calls instruction= once per turn when it's a callable (not a fixed
    string), so this window is always current rather than frozen at process
    start. Note: a callable instruction bypasses ADK's normal
    {{session_state}} templating entirely (see LlmAgent.canonical_instruction
    — bypass_state_injection is True whenever instruction is callable), so
    job_id has to be read directly off ctx.state here rather than left as a
    {{triaged_job_id}} placeholder for ADK to fill in. Found the hard way:
    the first version of this fix left the placeholder in and Tempo got
    queried for the literal string "triaged_job_id" as the job id.
    """
    from datetime import datetime, timedelta, timezone

    # triaged_job_id can carry a trailing reasoning line (TriageAgent's
    # instruction allows one) — same first-line-only handling as
    # capture_demo_mode.py uses for the same field.
    job_id = ctx.state.get("triaged_job_id", "unknown-job").strip().splitlines()[0].strip()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f"Given job_id={job_id}, use the Tempo tools (via Grafana MCP) to "
        f"inspect per-frame render spans for this job. Pass these exact literal RFC3339 "
        f'strings as the time range arguments: start="{start}", end="{end}" — do not '
        "compute, format, or construct timestamps yourself; use these two strings verbatim."
        " Report unusually long spans, orphaned/retried spans, or 'clean'."
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
            "to check CPU utilization, queue depth, and node churn for this job's worker "
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
        instruction=_tempo_instruction,
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
