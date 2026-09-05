"""Render the demo job's real frame batch: a contiguous range of the film
rendered under the low_samples fault, so the Demo Mode recording is grounded
in a real range of genuinely defective frames rather than one frame copied
around.

This matters for honesty, not just polish: a bad Cycles sample-count setting
on a render job affects every frame that job renders, not one. The impact
math ("N frames must be re-rendered") is only credible if N real defective
frames actually exist.

Routes through worker/render_worker.py's render_frame() (not a separate direct
Blender call) so this batch actually produces the same real OTLP metrics/logs/
traces a live backlot render would — previously this script bypassed the
worker entirely, which was one of the two reasons no telemetry had ever
actually reached Grafana.

Usage:
    python backlot/render_demo_batch.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backlot" / "worker"))
from render_worker import render_frame  # noqa: E402

BLEND_FILE = REPO_ROOT / "backlot" / "assets" / "movie.blend"
OUT_DIR = REPO_ROOT / "backlot" / "frames_local" / "job-seq042-sh0420"
JOB_ID = "job-seq042-sh0420"
DEMO_RESOLUTION = (480, 240)  # keeps demo-capture renders fast

# Frames 181-192 of the shot — matches fixtures/shotlist.json, where sh0420
# has 12 frames left to render (240 total, 228 done).
FIRST_FRAME = 181
LAST_FRAME = 192


def main() -> None:
    if not BLEND_FILE.exists():
        raise FileNotFoundError(f"{BLEND_FILE} not found — see backlot/assets/README.md")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()

    results = []
    for frame in range(FIRST_FRAME, LAST_FRAME + 1):
        print(f"rendering frame {frame} (low_samples)...")
        results.append(
            render_frame(
                str(BLEND_FILE), frame, str(OUT_DIR), "low_samples", JOB_ID, resolution=DEMO_RESOLUTION
            )
        )

    failed = [r for r in results if r["exit_code"] != 0]
    if failed:
        raise RuntimeError(f"{len(failed)} frame(s) failed to render: {failed}")
    print(f"\nrendered {len(results)} real defective frames -> {OUT_DIR}")


if __name__ == "__main__":
    main()
