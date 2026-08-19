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
from pydantic import BaseModel, Field

MODEL = "gemini-2.5-flash"


class VisualVerdict(BaseModel):
    has_defect: bool = Field(description="True if visual_evidence describes a real visual defect, False if it describes a clean/undefective frame.")
    reasoning: str = Field(description="One sentence: why you read it that way.")


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
    )


verdict_agent = build_verdict_agent()
