from second_unit.tools.shotlist import get_shot_for_job, list_active_jobs


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
