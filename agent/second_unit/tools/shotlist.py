"""The shot list: which render jobs map to which shots, sequences, and deadlines.

Backed by Firestore in production. Falls back to a local JSON fixture when
GOOGLE_CLOUD_PROJECT isn't set, so the agent graph is runnable and testable
without live GCP credentials — this is what the day-7 vertical slice runs against
before Firestore is wired up.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from second_unit.schedule import Shot

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "shotlist.json"

_RELATIVE_PREFIX = "now+"


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


def _parse_due_at(value: str) -> datetime:
    """Parse due_at as UTC-aware, always.

    Supports a relative form ("now+2h", "now+90m") alongside absolute ISO
    timestamps. The relative form exists for a real reason: the fixture
    originally hardcoded 2026-08-18T09:00:00, which silently rotted into the
    past days later and made the agent report a 72-hour slip and ~$61,585 of
    overtime exposure for one wasted frame — arithmetic that was correct but
    nonsense, and which only gets worse the longer the project sits between
    submission and judging. A relative deadline keeps the demo telling the
    same, credible story whenever it's run.

    Absolute timestamps also normalize to UTC-aware here: the fixture (and
    the Firestore rows seeded from it) store naive ISO strings with no
    offset, and schedule.compute_impact compares against
    datetime.now(timezone.utc), which raises on a naive/aware mismatch.
    Found during the day-7 vertical slice test — fixed at the parsing
    boundary so every Shot.due_at is aware the moment it's constructed.
    """
    if value.startswith(_RELATIVE_PREFIX):
        amount = value[len(_RELATIVE_PREFIX):].strip()
        unit = amount[-1]
        qty = float(amount[:-1])
        if unit == "h":
            delta = timedelta(hours=qty)
        elif unit == "m":
            delta = timedelta(minutes=qty)
        else:
            raise ValueError(f"unsupported relative due_at unit in {value!r} (use 'h' or 'm')")
        return datetime.now(timezone.utc) + delta

    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def get_shot_for_job(job_id: str) -> Optional[Shot]:
    """Resolve a render-farm job id to the Shot it belongs to.

    Production: query Firestore collection `shots` where `job_ids` array-contains job_id.
    Local/test: read fixtures/shotlist.json (see backlot/ for how jobs are minted).
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        from google.cloud import firestore  # imported lazily so tests don't need the SDK configured

        from google.cloud.firestore_v1.base_query import FieldFilter

        db = firestore.Client(project=project)
        docs = (
            db.collection("shots")
            .where(filter=FieldFilter("job_ids", "array_contains", job_id))
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
                due_at=_parse_due_at(d["due_at"]),
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
                due_at=_parse_due_at(d["due_at"]),
                client_review=d.get("client_review", False),
            )
    return None


def list_active_jobs() -> list[str]:
    """All job ids currently tracked, for TriageAgent to scan.

    Must mirror get_shot_for_job's Firestore-vs-fixture branch exactly — an
    earlier version always read the local fixture here regardless of
    GOOGLE_CLOUD_PROJECT, so in a real deployment TriageAgent would list
    fixture job ids that get_shot_for_job could never resolve against
    Firestore, silently filtering out every candidate. Found during the
    day-7 vertical slice test.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    ids: list[str] = []
    if project:
        from google.cloud import firestore  # lazy import, see get_shot_for_job

        db = firestore.Client(project=project)
        for doc in db.collection("shots").stream():
            ids.extend(doc.to_dict().get("job_ids", []))
        return ids

    for d in _load_fixture():
        ids.extend(d["job_ids"])
    return ids
