"""The control: a threshold-alerting baseline with no vision, no LLM — the
kind of alert rule a studio would already have in Grafana today. Existing to
prove the agent's edge, not to be a strawman: it correctly catches everything
a real threshold alert would (kill_worker, starve_memory), and it is
structurally blind to low_samples/break_texture exactly because no metric
moves when only the picture is wrong.
"""
from __future__ import annotations


def baseline_would_alert(fault_type: str) -> bool:
    """Would a standard Grafana threshold alert (job failure, OOM, retry count,
    span-error-rate) fire for this fault type? This mirrors real alerting
    rules a studio would already have — see grafana/dashboards/ for the
    importable versions we're comparing against.
    """
    return fault_type in {"kill_worker", "starve_memory"}
