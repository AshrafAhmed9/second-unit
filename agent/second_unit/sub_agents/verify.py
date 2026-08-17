"""3. LoopAgent "verify" — a skeptic challenges each visual finding before it's
trusted. Kept only because it measurably cuts the false-positive rate — see
eval/harness.py, which scores detection WITH and WITHOUT this loop so the
claim is provable, not asserted.
"""
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools.load_artifacts_tool import load_artifacts_tool

from second_unit.sub_agents.evidence import _load_frames_tool

MODEL = "gemini-2.5-flash"

skeptic_agent = LlmAgent(
    name="SkepticAgent",
    model=MODEL,
    instruction=(
        "You are reviewing a visual-defect claim from EyesAgent: "
        "{{visual_evidence}}. Be genuinely skeptical: could this be a stylistic "
        "choice, a motion-blur artifact, or normal grain rather than a real "
        "defect? If the claim is well-supported and specific (names a frame and "
        "a concrete defect), say CONFIRMED. If it is vague or plausibly benign, "
        "say REJECTED and state exactly what re-examination is needed."
    ),
    output_key="skeptic_verdict",
)

reexamine_agent = LlmAgent(
    name="ReexamineAgent",
    model="gemini-2.5-pro",
    instruction=(
        "The skeptic rejected the prior visual-defect claim: {{skeptic_verdict}}. "
        "Given job_id={{triaged_job_id}}: (1) call load_frames to re-fetch the "
        "frame artifacts, (2) call load_artifacts with the artifact_names it "
        "returns to actually load the pixel data, (3) look at the loaded image "
        "yourself and produce a sharper, more specific finding, or concede the "
        "frames are genuinely clean. You MUST actually call both tools and look "
        "at the real image before answering — do not narrate what a tool call "
        "would look like or describe an image without having loaded it. "
        "Update visual_evidence with your revised, final assessment."
    ),
    tools=[_load_frames_tool, load_artifacts_tool],
    output_key="visual_evidence",
)

verify_loop = LoopAgent(
    name="VerifyLoop",
    sub_agents=[skeptic_agent, reexamine_agent],
    max_iterations=3,
)
