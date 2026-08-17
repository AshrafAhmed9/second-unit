"""Fan out a render job across Cloud Run Jobs (production) or local subprocess
(day-1/day-7 spike, before GCP is wired up).

Usage:
    # local, no GCP creds needed — this is what the day-7 vertical slice runs:
    python dispatch.py --job-id job-seq042-sh0420 --frame-start 1180 \
        --frame-end 1194 --condition low_samples --local

    # production, real Cloud Run Jobs fan-out:
    python dispatch.py --job-id job-seq042-sh0420 --frame-start 1180 \
        --frame-end 1194 --condition low_samples
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path

WORKER_SCRIPT = Path(__file__).parent / "worker" / "render_worker.py"
BLEND_FILE = Path(__file__).parent / "assets" / "movie.blend"  # see backlot/assets/README.md


def dispatch_local(job_id: str, frame_start: int, frame_end: int, condition: str, out_dir: str) -> None:
    """Run the worker in-process. This is the path with zero cloud dependency
    — used to prove the vertical slice on day 7 before Cloud Run Jobs exists.
    """
    cmd = [
        sys.executable,
        str(WORKER_SCRIPT),
        "--job-id", job_id,
        "--blend", str(BLEND_FILE),
        "--frame-start", str(frame_start),
        "--frame-end", str(frame_end),
        "--out", out_dir,
        "--condition", condition,
    ]

    if condition == "kill_worker":
        # Real process kill applied at dispatch level, per conditions/kill_worker.yaml.
        proc = subprocess.Popen(cmd)
        time.sleep(random.uniform(2, 6))
        proc.kill()
        print(f"[dispatch] SIGKILLed worker pid={proc.pid} mid-render (kill_worker condition)")
        # A real retry: relaunch the same range once, unthrottled.
        subprocess.run(cmd, check=True)
        return

    subprocess.run(cmd, check=True)


def dispatch_cloud_run_jobs(job_id: str, frame_start: int, frame_end: int, condition: str) -> None:
    """Submit the render as a Cloud Run Jobs execution, one task per frame
    range, via `gcloud run jobs execute`. Memory cap for starve_memory comes
    from conditions/starve_memory.yaml.
    """
    memory = "512Mi" if condition == "starve_memory" else "2Gi"
    cmd = [
        "gcloud", "run", "jobs", "execute", "backlot-render-worker",
        "--args", f"--job-id={job_id},--frame-start={frame_start},--frame-end={frame_end},--condition={condition}",
        "--memory", memory,
        "--wait",
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--condition", default="clean")
    parser.add_argument("--out", default="./backlot/frames_local")
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()

    out_dir = f"{args.out}/{args.job_id}"
    if args.local:
        dispatch_local(args.job_id, args.frame_start, args.frame_end, args.condition, out_dir)
    else:
        dispatch_cloud_run_jobs(args.job_id, args.frame_start, args.frame_end, args.condition)


if __name__ == "__main__":
    main()
