"""Deterministic deadline/cost math. Pure functions, no LLM calls, unit-tested.

This module exists because the agent's headline claim — "this failure costs you
$X and Y hours" — must be arithmetic a human can audit, not something an LLM
free-associated. The LLM decides WHICH shot and WHAT evidence; this module
converts that into a number.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


GPU_HOUR_COST_USD = 2.10          # blended on-demand GPU rate, documented in README
OVERTIME_CREW_RATE_USD_PER_HOUR = 850  # a full second-unit crew on overtime, documented estimate


@dataclass(frozen=True)
class Shot:
    shot_id: str
    sequence: str
    frames_total: int
    frames_done: int
    render_minutes_per_frame: float
    due_at: datetime          # e.g. next dailies screening
    client_review: bool = False


@dataclass(frozen=True)
class Impact:
    shot_id: str
    wasted_gpu_hours: float
    wasted_cost_usd: float
    delay_hours: float
    misses_deadline: bool
    overtime_cost_usd: float
    headline: str


def compute_impact(shot: Shot, wasted_frames: int, now: datetime) -> Impact:
    """Turn a raw defect count into schedule slip and dollar cost.

    wasted_frames: frames that must be re-rendered because of the detected defect.
    """
    if wasted_frames < 0:
        raise ValueError("wasted_frames must be >= 0")

    wasted_gpu_hours = round((wasted_frames * shot.render_minutes_per_frame) / 60, 2)
    wasted_cost_usd = round(wasted_gpu_hours * GPU_HOUR_COST_USD, 2)

    remaining_frames = shot.frames_total - shot.frames_done
    total_remaining_minutes = remaining_frames * shot.render_minutes_per_frame
    rework_minutes = wasted_frames * shot.render_minutes_per_frame
    projected_finish = now + timedelta(minutes=total_remaining_minutes + rework_minutes)

    delay_hours = max(0.0, (projected_finish - shot.due_at).total_seconds() / 3600)
    misses_deadline = projected_finish > shot.due_at

    overtime_cost_usd = round(delay_hours * OVERTIME_CREW_RATE_USD_PER_HOUR, 2) if misses_deadline else 0.0

    headline = (
        f"{shot.sequence}/{shot.shot_id}: {wasted_frames} frame(s) must be "
        f"re-rendered ({wasted_gpu_hours} GPU-hours, ${wasted_cost_usd:,.0f}). "
    )
    if misses_deadline:
        headline += (
            f"Projected finish slips {delay_hours:.1f}h past the "
            f"{shot.due_at.strftime('%H:%M')} deadline"
            + (" (client review)" if shot.client_review else "")
            + f" — ~${overtime_cost_usd:,.0f} overtime exposure."
        )
    else:
        headline += "Still on schedule, but margin is shrinking."

    return Impact(
        shot_id=shot.shot_id,
        wasted_gpu_hours=wasted_gpu_hours,
        wasted_cost_usd=wasted_cost_usd,
        delay_hours=round(delay_hours, 2),
        misses_deadline=misses_deadline,
        overtime_cost_usd=overtime_cost_usd,
        headline=headline,
    )
