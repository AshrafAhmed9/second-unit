"""3. LoopAgent "verify" — a skeptic challenges each visual finding before it's
trusted. Kept only because it measurably cuts the false-positive rate — see
eval/harness.py, which scores detection WITH and WITHOUT this loop so the
claim is provable, not asserted.
"""
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import ToolContext
from google.adk.tools.load_artifacts_tool import load_artifacts_tool

from second_unit.sub_agents.evidence import _load_frames_tool

MODEL = "gemini-2.5-flash"


def _exit_loop(tool_context: ToolContext) -> dict:
    """Call this when your verdict is CONFIRMED and no further re-examination
    is needed — stops the loop immediately instead of running the remaining
    rounds. Without this, an earlier version always ran the full
    max_iterations regardless of outcome: once the skeptic had already
    confirmed a finding on round 1, rounds 2-3 had nothing real left to
    examine and produced degraded filler ("Acknowledged.", "DONE") or, once
    observed, an outright fabricated new critique ("unrealistic shadows") on
    a genuinely clean render just to have something to say — and because
    visual_evidence is overwritten each round, THAT garbage final-round text
    is what the rest of the graph saw. Found scoring the first real eval run:
    3 of 3 clean/kill_worker conditions were misread as defects this way.
    """
    tool_context.actions.escalate = True
    return {"status": "confirmed, loop exiting"}


def build_verify_loop() -> LoopAgent:
    """Factory, not a singleton — see build_evidence_agents() in evidence.py
    for why: an ADK agent can only have one parent, so anything that runs
    this more than once per process (eval/harness.py) needs fresh instances.
    """
    skeptic_agent = LlmAgent(
        name="SkepticAgent",
        model=MODEL,
        instruction=(
            "You are reviewing a visual-defect claim from EyesAgent: "
            "{{visual_evidence}}. Be genuinely skeptical: could this be a stylistic "
            "choice, a motion-blur artifact, or normal grain rather than a real "
            "defect? If the claim is well-supported and specific (names a frame and "
            "a concrete defect), say CONFIRMED and immediately call exit_loop — "
            "do not invent additional critiques once you've confirmed a verdict. "
            "If it is vague or plausibly benign, say REJECTED and state exactly "
            "what re-examination is needed, and do NOT call exit_loop."
        ),
        tools=[_exit_loop],
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

    return LoopAgent(
        name="VerifyLoop",
        sub_agents=[skeptic_agent, reexamine_agent],
        max_iterations=3,
    )


verify_loop = build_verify_loop()
