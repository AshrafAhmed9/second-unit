"""The shot list: which render jobs map to which shots, sequences, and deadlines.

Backed by Firestore in production. Falls back to a local JSON fixture when
GOOGLE_CLOUD_PROJECT isn't set, so the agent graph is runnable and testable
without live GCP credentials — this is what the day-7 vertical slice runs against
before Firestore is wired up.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from second_unit.schedule import Shot

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "shotlist.json"


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


def get_shot_for_job(job_id: str) -> Optional[Shot]:
    """Resolve a render-farm job id to the Shot it belongs to.

    Production: query Firestore collection `shots` where `job_ids` array-contains job_id.
    Local/test: read fixtures/shotlist.json (see backlot/ for how jobs are minted).
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        from google.cloud import firestore  # imported lazily so tests don't need the SDK configured

        db = firestore.Client(project=project)
        docs = (
            db.collection("shots")
            .where("job_ids", "array_contains", job_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            return Shot(
                shot_id=d["shot_id"],
                sequence=d["sequence"],
                frames_total=d["frames_total"],
                frames_done=d["frames_done"],
                render_minutes_per_frame=d["render_minutes_per_frame"],
                due_at=datetime.fromisoformat(d["due_at"]),
                client_review=d.get("client_review", False),
            )
        return None

    for d in _load_fixture():
        if job_id in d["job_ids"]:
            return Shot(
                shot_id=d["shot_id"],
                sequence=d["sequence"],
                frames_total=d["frames_total"],
                frames_done=d["frames_done"],
                render_minutes_per_frame=d["render_minutes_per_frame"],
                due_at=datetime.fromisoformat(d["due_at"]),
                client_review=d.get("client_review", False),
            )
    return None


def list_active_jobs() -> list[str]:
    """All job ids currently tracked, for TriageAgent to scan."""
    ids: list[str] = []
    for d in _load_fixture():
        ids.extend(d["job_ids"])
    return ids
