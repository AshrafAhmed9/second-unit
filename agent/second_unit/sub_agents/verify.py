"""3. LoopAgent "verify" — a skeptic challenges each visual finding before it's
trusted. Kept only because it measurably cuts the false-positive rate — see
eval/harness.py, which scores detection WITH and WITHOUT this loop so the
claim is provable, not asserted.
"""
from google.adk.agents import LlmAgent, LoopAgent

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
        "Re-examine the same frames (call load_frames again if needed) and either "
        "produce a sharper, more specific finding, or concede the frames are clean. "
        "Update visual_evidence with your revised, final assessment."
    ),
    output_key="visual_evidence",
)

verify_loop = LoopAgent(
    name="VerifyLoop",
    sub_agents=[skeptic_agent, reexamine_agent],
    max_iterations=3,
)
