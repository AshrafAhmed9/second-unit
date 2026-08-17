"""Fetch rendered frames for a job and hand them to Gemini as image parts.

Production: frames live in GCS at gs://{bucket}/{job_id}/frame_XXXX.png, written
by backlot/worker (see backlot/). Local/test: reads from backlot/frames_local/.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

LOCAL_FRAMES_ROOT = Path(__file__).resolve().parents[3] / "backlot" / "frames_local"


def list_frames(job_id: str) -> list[str]:
    """Return frame identifiers (paths or GCS URIs) for a job, sorted."""
    bucket = os.environ.get("BACKLOT_BUCKET")
    if bucket:
        from google.cloud import storage  # lazy import

        client = storage.Client()
        blobs = client.list_blobs(bucket, prefix=f"{job_id}/")
        return sorted(f"gs://{bucket}/{b.name}" for b in blobs if b.name.endswith(".png"))

    job_dir = LOCAL_FRAMES_ROOT / job_id
    if not job_dir.exists():
        return []
    return sorted(str(p) for p in job_dir.glob("*.png"))


def load_frame_bytes(frame_ref: str) -> bytes:
    """Load raw bytes for one frame, from GCS or local disk."""
    if frame_ref.startswith("gs://"):
        from google.cloud import storage  # lazy import

        _, _, rest = frame_ref.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(blob_name)
        return blob.download_as_bytes()

    return Path(frame_ref).read_bytes()


def as_gemini_image_parts(frame_refs: Iterable[str]):
    """Convert frame references into google-genai Part objects for a vision call."""
    from google.genai import types

    parts = []
    for ref in frame_refs:
        data = load_frame_bytes(ref)
        parts.append(types.Part.from_bytes(data=data, mime_type="image/png"))
    return parts
