"""The root agent graph.

Split into two SequentialAgents rather than one, because the human-approval
gate (item 6 in the plan's graph) is a real interrupt point: nothing after
PlannerAgent runs until a person clicks approve in the control room. See
server.py for how these two halves are invoked with the approval boundary
between them.

    SequentialAgent "diagnose"          [HUMAN APPROVAL GATE]   SequentialAgent "act"
    1. TriageAgent                              (server.py)      7. ActuatorAgent
    2. ParallelAgent "evidence"          ---------------------->
       (metrics, logs, traces, eyes)
    3. LoopAgent "verify"
    4. ImpactAgent
    5. PlannerAgent
"""
from google.adk.agents import SequentialAgent

from second_unit.sub_agents import (
    actuator_agent,
    evidence_agents,
    impact_agent,
    planner_agent,
    triage_agent,
    verify_loop,
)
from second_unit.telemetry import configure_tracing

configure_tracing()

diagnose_agent = SequentialAgent(
    name="SecondUnitDiagnose",
    sub_agents=[triage_agent, evidence_agents, verify_loop, impact_agent, planner_agent],
)

act_agent = SequentialAgent(
    name="SecondUnitAct",
    sub_agents=[actuator_agent],
)

# ADK CLI / dev UI entrypoint (`adk web` / `adk run`) expects a module-level
# `root_agent`. Points at the pre-approval half so `adk web` is safe to run
# without accidentally writing to Grafana.
root_agent = diagnose_agent
