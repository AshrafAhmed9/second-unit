from datetime import datetime, timedelta, timezone

import pytest

from second_unit.schedule import Shot, compute_impact


def make_shot(**overrides) -> Shot:
    defaults = dict(
        shot_id="sh0420",
        sequence="seq042",
        frames_total=240,
        frames_done=180,
        render_minutes_per_frame=6.5,
        due_at=datetime.now(timezone.utc) + timedelta(hours=6),
        client_review=True,
    )
    defaults.update(overrides)
    return Shot(**defaults)


def test_no_waste_never_misses_deadline_when_comfortably_ahead():
    shot = make_shot(frames_done=239, due_at=datetime.now(timezone.utc) + timedelta(hours=6))
    impact = compute_impact(shot, wasted_frames=0, now=datetime.now(timezone.utc))
    assert impact.wasted_gpu_hours == 0
    assert impact.wasted_cost_usd == 0
    assert impact.misses_deadline is False
    assert impact.overtime_cost_usd == 0


def test_wasted_frames_produce_positive_cost_and_gpu_hours():
    shot = make_shot()
    impact = compute_impact(shot, wasted_frames=14, now=datetime.now(timezone.utc))
    assert impact.wasted_gpu_hours == pytest.approx(round((14 * 6.5) / 60, 2), abs=1e-9)
    assert impact.wasted_cost_usd > 0
    assert "sh0420" in impact.headline


def test_enough_rework_pushes_finish_past_a_tight_deadline():
    tight_due = datetime.now(timezone.utc) + timedelta(hours=1)
    shot = make_shot(frames_done=0, frames_total=100, render_minutes_per_frame=5, due_at=tight_due)
    impact = compute_impact(shot, wasted_frames=50, now=datetime.now(timezone.utc))
    assert impact.misses_deadline is True
    assert impact.overtime_cost_usd > 0
    assert impact.delay_hours > 0


def test_negative_wasted_frames_rejected():
    shot = make_shot()
    with pytest.raises(ValueError):
        compute_impact(shot, wasted_frames=-1, now=datetime.now(timezone.utc))


def test_client_review_flag_appears_in_headline_when_deadline_missed():
    tight_due = datetime.now(timezone.utc) + timedelta(minutes=10)
    shot = make_shot(frames_done=0, frames_total=50, render_minutes_per_frame=5, due_at=tight_due, client_review=True)
    impact = compute_impact(shot, wasted_frames=10, now=datetime.now(timezone.utc))
    assert impact.misses_deadline is True
    assert "client review" in impact.headline
