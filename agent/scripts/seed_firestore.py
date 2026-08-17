"""One-time seed: push agent/fixtures/shotlist.json into real Firestore, so
the production code path in tools/shotlist.py (not just its local-fixture
fallback) has real data to read during development and the eval harness.
"""
import json
from pathlib import Path

from google.cloud import firestore

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "shotlist.json"


def main():
    db = firestore.Client()
    rows = json.loads(FIXTURE_PATH.read_text())
    for row in rows:
        db.collection("shots").document(row["shot_id"]).set(row)
        print(f"seeded {row['shot_id']}")


if __name__ == "__main__":
    main()
