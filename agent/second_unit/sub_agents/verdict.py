"""VerdictAgent — turns the free-text visual_evidence narrative into a clean
structured boolean.

Why this exists: two different keyword-heuristic classifiers were tried and
tuned directly against visual_evidence text in eval/harness.py, and both
failed in predictable, embarrassing ways in opposite directions — one
scored a real detection ("I have found visual artifacts... noise") as not
flagged because its exact phrasing didn't match a "clean" string being
checked for; the other then scored a real negation ("There are no visual
defects... The frame is clean") as flagged, because "defect" appeared as a
substring regardless of the "no" in front of it. That's not a tuning
problem, it's evidence that parsing prose with string matching is the wrong
tool for a question that has a real, structured answer.

Deliberately a SEPARATE agent from EyesAgent/ReexamineAgent rather than
giving them output_schema directly: those agents need `tools` (load_frames,
load_artifacts) to gather evidence before answering, and mixing
tool-calling with a strict structured final response is an unproven
combination at runtime this late in the build to gamble on. This agent has
no tools at all — it only ever reads the already-finalized narrative — so
structured output has nothing to conflict with.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field

from second_unit.telemetry import get_meter

MODEL = "gemini-2.5-flash"


class VisualVerdict(BaseModel):
    has_defect: bool = Field(description="True if visual_evidence describes a real visual defect, False if it describes a clean/undefective frame.")
    reasoning: str = Field(description="One sentence: why you read it that way.")


_frames_inspected_counter = None
_defects_detected_counter = None


def _get_verdict_counters():
    """Lazily create the two counter instruments on first use, not at module
    import time. sub_agents/ is imported before agent.py's configure_tracing()
    call runs (see agent.py), so resolving get_meter() at import time would
    bind these instruments to a not-yet-configured (no-op) MeterProvider.
    Creating them once and caching, rather than calling create_counter() on
    every verdict, avoids re-registering the same instrument on every run.
    """
    global _frames_inspected_counter, _defects_detected_counter
    if _frames_inspected_counter is None:
        meter = get_meter("second-unit-agent")
        _frames_inspected_counter = meter.create_counter(
            "second_unit_frames_inspected_total",
            description="Jobs whose rendered frames VerdictAgent classified.",
        )
        _defects_detected_counter = meter.create_counter(
            "second_unit_visual_defects_detected_total",
            description="VerdictAgent verdicts where the frame was flagged as defective.",
        )
    return _frames_inspected_counter, _defects_detected_counter


def _emit_verdict_metrics(callback_context: CallbackContext) -> None:
    """Turns the structured has_defect verdict into a Prometheus counter over
    the same OTLP pipeline render_worker.py already pushes CPU/render metrics
    on. This is the payoff of the whole vision-agent idea: a failure class
    that plain metrics/logs monitoring structurally cannot see becomes a
    normal, alertable time series, not just prose in a chat transcript.
    """
    verdict = callback_context.state.get("visual_verdict")
    if verdict is None:
        return
    has_defect = verdict["has_defect"] if isinstance(verdict, dict) else verdict.has_defect
    job_id = str(callback_context.state.get("triaged_job_id", "unknown")).strip().splitlines()[0].strip()

    frames_counter, defects_counter = _get_verdict_counters()
    frames_counter.add(1, {"job_id": job_id})
    defects_counter.add(1 if has_defect else 0, {"job_id": job_id})


def build_verdict_agent() -> LlmAgent:
    """Factory, not a singleton — see build_evidence_agents() in evidence.py
    for why (ADK agents can only have one parent; eval/harness.py needs a
    fresh instance per scored condition).
    """
    return LlmAgent(
        name="VerdictAgent",
        model=MODEL,
        instruction=(
            "Read this visual finding: {{visual_evidence}}. Does it describe a "
            "REAL visual defect (noise, fireflies, corruption, missing/wrong "
            "textures, black/blank frames, etc.), or does it describe a clean, "
            "correctly-rendered frame? Watch for negation carefully — 'there are "
            "no defects' and 'the frame is clean' both mean has_defect=false, "
            "even though the word 'defect' or 'artifact' may appear in the text. "
            "Answer strictly from what visual_evidence actually says."
        ),
        output_schema=VisualVerdict,
        output_key="visual_verdict",
        after_agent_callback=_emit_verdict_metrics,
    )


verdict_agent = build_verdict_agent()
