from datetime import datetime, timezone

import pytest

from second_unit.tools.shotlist import _parse_due_at, get_shot_for_job, list_active_jobs


def test_list_active_jobs_reads_local_fixture():
    jobs = list_active_jobs()
    assert "job-seq042-sh0420" in jobs
    assert "job-seq011-sh0110" in jobs


def test_get_shot_for_job_resolves_fixture_row():
    shot = get_shot_for_job("job-seq042-sh0420")
    assert shot is not None
    assert shot.shot_id == "sh0420"
    assert shot.sequence == "seq042"
    assert shot.client_review is True


def test_get_shot_for_job_returns_none_for_unknown_job():
    assert get_shot_for_job("job-does-not-exist") is None


def test_due_at_is_always_timezone_aware():
    """compute_impact compares due_at against an aware datetime.now(utc);
    a naive value raises TypeError at runtime.
    """
    assert get_shot_for_job("job-seq042-sh0420").due_at.tzinfo is not None
    assert _parse_due_at("2026-08-18T09:00:00").tzinfo is not None
    assert _parse_due_at("2026-08-18T09:00:00+00:00").tzinfo is not None


def test_relative_due_at_resolves_into_the_future():
    """The fixture uses relative deadlines so the demo can't rot into
    reporting a multi-day slip for one wasted frame.
    """
    before = datetime.now(timezone.utc)
    two_hours = _parse_due_at("now+2h")
    ninety_min = _parse_due_at("now+90m")

    assert 1.9 < (two_hours - before).total_seconds() / 3600 < 2.1
    assert 89 < (ninety_min - before).total_seconds() / 60 < 91


def test_relative_due_at_rejects_unknown_unit():
    with pytest.raises(ValueError):
        _parse_due_at("now+3d")


def test_demo_shot_is_tight_but_makeable_without_defects():
    """The demo's story depends on this: sh0420 must be on schedule when
    nothing is wrong, so that a real defect is what tips it over. If this
    fails, the fixture's frame counts and due_at have drifted apart and the
    recorded demo will tell the wrong story.
    """
    shot = get_shot_for_job("job-seq042-sh0420")
    remaining_minutes = (shot.frames_total - shot.frames_done) * shot.render_minutes_per_frame
    minutes_available = (shot.due_at - datetime.now(timezone.utc)).total_seconds() / 60

    assert remaining_minutes < minutes_available, "no slack: shot is already late before any defect"
    assert remaining_minutes > minutes_available * 0.5, "too much slack: a real defect won't tip the deadline"
