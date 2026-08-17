"""THE REAL RENDER FARM WORKER.

Runs headless Blender against a real CC-BY open-movie .blend file and emits
genuine Prometheus (via pushgateway/remote_write), Loki, and OTLP trace signal
for every frame it renders — including when a fault `condition` is injected
that makes the render finish "successfully" while producing a visually broken
frame. That contradiction (green telemetry, bad picture) is the entire thesis
of this project, so it must come from a render that actually happened.

Usage:
    python render_worker.py --job-id job-seq042-sh0420 --blend movie.blend \
        --frame-start 1180 --frame-end 1194 --out /frames --condition low_samples

Conditions (see backlot/conditions/*.yaml for the full definitions):
    clean          — normal render, no fault
    low_samples    — drop Cycles samples drastically -> real denoiser fireflies,
                     job still exits 0, metrics stay green
    kill_worker    — SIGKILL mid-frame on a random frame -> real retry, real
                     orphaned span in Tempo
    starve_memory  — cap the container's memory below what the frame needs ->
                     real OOM kill
    break_texture  — repoint a texture path to a nonexistent file -> real
                     renderer stderr, real visually-wrong (pink/missing) frame
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from opentelemetry import trace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
from second_unit.telemetry import configure_tracing  # noqa: E402

tracer = configure_tracing(service_name="second-unit-backlot")


def build_blender_command(
    blend_path: str, frame: int, out_dir: str, condition: str
) -> list[str]:
    """Construct the actual `blender --background ... --render-frame` invocation,
    with the fault condition applied via Blender's Python expression flag so the
    defect is produced by Blender itself, not faked after the fact.
    """
    cmd = [
        "blender",
        "--background",
        blend_path,
        "--render-output",
        f"{out_dir}/frame_",
        "--use-extension",
        "1",
    ]

    if condition == "low_samples":
        # Real fault: crank Cycles samples down to near-nothing. The render
        # still succeeds (exit 0) but produces genuine denoiser noise.
        cmd += ["--python-expr", "import bpy; bpy.context.scene.cycles.samples = 2"]
    elif condition == "break_texture":
        cmd += [
            "--python-expr",
            "import bpy\n"
            "for img in bpy.data.images:\n"
            "    img.filepath = '/nonexistent/broken_texture.png'\n",
        ]
    # kill_worker and starve_memory are applied at the process/container level
    # by dispatch.py, not via Blender flags — see conditions/kill_worker.yaml
    # and conditions/starve_memory.yaml.

    cmd += ["--render-frame", str(frame)]
    return cmd


def render_frame(blend_path: str, frame: int, out_dir: str, condition: str, job_id: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    cmd = build_blender_command(blend_path, frame, out_dir, condition)

    with tracer.start_as_current_span("backlot.render_frame") as span:
        span.set_attribute("job_id", job_id)
        span.set_attribute("frame", frame)
        span.set_attribute("condition", condition)

        started = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        duration_s = time.time() - started

        span.set_attribute("duration_s", duration_s)
        span.set_attribute("exit_code", result.returncode)
        if result.returncode != 0:
            span.set_attribute("stderr", result.stderr[-4000:])

        emit_metrics(job_id=job_id, frame=frame, duration_s=duration_s, exit_code=result.returncode)
        emit_logs(job_id=job_id, frame=frame, condition=condition, stderr=result.stderr)

        return {
            "job_id": job_id,
            "frame": frame,
            "exit_code": result.returncode,
            "duration_s": duration_s,
            "condition": condition,
        }


def emit_metrics(job_id: str, frame: int, duration_s: float, exit_code: int) -> None:
    """Push real render-worker metrics to Grafana Cloud via the Prometheus
    remote-write endpoint. This is what stays GREEN even on a low_samples
    render — the job succeeded, so nothing here alerts.
    """
    endpoint = os.environ.get("PROMETHEUS_REMOTE_WRITE_URL")
    if not endpoint:
        print(f"[metrics:local] job={job_id} frame={frame} duration_s={duration_s:.1f} exit={exit_code}")
        return

    import requests  # local import: only needed when actually pushing

    # Minimal remote_write client. In production, prefer the OTel Collector's
    # Prometheus remote-write exporter fed by an OTLP metrics pipeline — this
    # direct-push path is the fast path for the day-3/day-7 spike.
    requests.post(
        endpoint,
        auth=(os.environ["GRAFANA_CLOUD_METRICS_USER"], os.environ["GRAFANA_CLOUD_METRICS_TOKEN"]),
        headers={"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy"},
        data=_encode_remote_write_sample(job_id, frame, duration_s, exit_code),
        timeout=10,
    )


def emit_logs(job_id: str, frame: int, condition: str, stderr: str) -> None:
    """Push renderer stderr/stdout to Grafana Cloud Loki so LogsAgent has real
    log lines to search — including genuine Blender error output when
    break_texture is active.
    """
    endpoint = os.environ.get("LOKI_PUSH_URL")
    if not endpoint:
        if stderr.strip():
            print(f"[logs:local] job={job_id} frame={frame} condition={condition} stderr={stderr[-500:]}")
        return

    import requests  # local import

    requests.post(
        endpoint,
        auth=(os.environ["GRAFANA_CLOUD_LOGS_USER"], os.environ["GRAFANA_CLOUD_LOGS_TOKEN"]),
        json={
            "streams": [
                {
                    "stream": {"job": "backlot-worker", "job_id": job_id, "condition": condition},
                    "values": [[str(int(time.time() * 1e9)), stderr or "render ok"]],
                }
            ]
        },
        timeout=10,
    )


def _encode_remote_write_sample(job_id: str, frame: int, duration_s: float, exit_code: int) -> bytes:
    """Placeholder for the real snappy-compressed protobuf WriteRequest.
    Swap for `prometheus-client` + `remote-write` helper (e.g. `prometheus_remote_writer`)
    during the day-1/day-3 spike — flagged in the plan as an open item.
    """
    raise NotImplementedError(
        "wire a real Prometheus remote-write encoder here (e.g. the "
        "`remote-write-exporter` pattern via OTel Collector, or "
        "`prometheus-remote-writer` package) once Grafana Cloud creds exist"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--blend", required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--condition", default="clean")
    args = parser.parse_args()

    results = []
    for frame in range(args.frame_start, args.frame_end + 1):
        results.append(render_frame(args.blend, frame, args.out, args.condition, args.job_id))

    failed = [r for r in results if r["exit_code"] != 0]
    print(f"rendered {len(results)} frames, {len(failed)} nonzero exit")


if __name__ == "__main__":
    main()
