"""THE REAL RENDER FARM WORKER.

Runs headless Blender against a real CC-BY open-movie .blend file and emits
genuine metrics, logs, and traces to Grafana Cloud over one OTLP gateway
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
import logging
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

from opentelemetry import trace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
from second_unit.telemetry import configure_tracing, get_log_handler, get_meter  # noqa: E402

_SERVICE_NAME = "second-unit-backlot"
tracer = configure_tracing(service_name=_SERVICE_NAME)
_meter = get_meter(_SERVICE_NAME)

# Dashboard-facing metric names — must match grafana/dashboards/second-unit-ops-wall.json.
# Named "cpu", not "gpu": these are headless Blender containers on Cloud Run
# Jobs with no GPU passthrough, so CPU utilization is the real number to report.
_cpu_util = _meter.create_gauge(
    "backlot_worker_cpu_utilization_ratio",
    description="Container CPU utilization during a frame render (0-1).",
)
_render_duration = _meter.create_histogram(
    "backlot_render_duration_seconds",
    description="Wall-clock time to render one frame.",
    unit="s",
)

_logger = logging.getLogger("second_unit.backlot")
_log_handler = get_log_handler(_SERVICE_NAME)
if _log_handler:
    _logger.addHandler(_log_handler)
    _logger.setLevel(logging.INFO)


def build_blender_command(
    blend_path: str, frame: int, out_dir: str, condition: str, resolution: tuple[int, int] | None = None
) -> list[str]:
    """Construct the actual `blender --background ... --render-frame` invocation,
    with the fault condition applied via Blender's Python expression flag so the
    defect is produced by Blender itself, not faked after the fact.

    `resolution` is an optional (width, height) override — used by
    render_demo_batch.py to keep demo-capture renders fast; omitted, Blender
    renders at the .blend file's native resolution.
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

    if resolution:
        w, h = resolution
        cmd += [
            "--python-expr",
            f"import bpy\nbpy.context.scene.render.resolution_x = {w}\nbpy.context.scene.render.resolution_y = {h}\n",
        ]

    if condition == "low_samples":
        # Real fault: crank Cycles samples down to near-nothing and disable
        # the denoiser. The render still succeeds (exit 0) but produces
        # genuine, severe denoiser noise.
        cmd += [
            "--python-expr",
            "import bpy\n"
            "bpy.context.scene.render.engine = 'CYCLES'\n"
            "bpy.context.scene.cycles.samples = 1\n"
            "bpy.context.scene.cycles.use_denoising = False\n",
        ]
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


def render_frame(
    blend_path: str,
    frame: int,
    out_dir: str,
    condition: str,
    job_id: str,
    resolution: tuple[int, int] | None = None,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    cmd = build_blender_command(blend_path, frame, out_dir, condition, resolution=resolution)

    with tracer.start_as_current_span("backlot.render_frame") as span:
        span.set_attribute("job_id", job_id)
        span.set_attribute("frame", frame)
        span.set_attribute("condition", condition)

        started = time.time()
        rusage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        duration_s = time.time() - started
        rusage_after = resource.getrusage(resource.RUSAGE_CHILDREN)

        # Real CPU utilization: actual child-process CPU seconds consumed
        # (user + system, from the OS's own accounting) divided by wall time
        # and core count. Not a synthetic number.
        cpu_s = (rusage_after.ru_utime - rusage_before.ru_utime) + (
            rusage_after.ru_stime - rusage_before.ru_stime
        )
        cpu_ratio = min(cpu_s / duration_s / os.cpu_count(), 1.0) if duration_s > 0 else 0.0

        span.set_attribute("duration_s", duration_s)
        span.set_attribute("exit_code", result.returncode)
        span.set_attribute("cpu_utilization_ratio", cpu_ratio)
        if result.returncode != 0:
            span.set_attribute("stderr", result.stderr[-4000:])

        emit_metrics(
            job_id=job_id, frame=frame, duration_s=duration_s, exit_code=result.returncode, cpu_ratio=cpu_ratio
        )
        emit_logs(job_id=job_id, frame=frame, condition=condition, stderr=result.stderr)

        return {
            "job_id": job_id,
            "frame": frame,
            "exit_code": result.returncode,
            "duration_s": duration_s,
            "condition": condition,
        }


def emit_metrics(job_id: str, frame: int, duration_s: float, exit_code: int, cpu_ratio: float) -> None:
    """Record real render-worker metrics via the OTLP metrics pipeline
    (agent/second_unit/telemetry.py), which Grafana Cloud's OTLP gateway
    converts into Prometheus series. This is what stays GREEN even on a
    low_samples render — the job succeeded, so nothing here alerts. Fixes the
    CRITICAL finding that the old Prometheus remote-write path was dead code
    (`_encode_remote_write_sample` raised NotImplementedError, so nothing was
    ever actually pushed).
    """
    attrs = {"job_id": job_id, "frame": str(frame), "exit_code": str(exit_code)}
    _cpu_util.set(cpu_ratio, attrs)
    _render_duration.record(duration_s, attrs)
    print(f"[metrics] job={job_id} frame={frame} duration_s={duration_s:.1f} cpu={cpu_ratio:.2f} exit={exit_code}")


def emit_logs(job_id: str, frame: int, condition: str, stderr: str) -> None:
    """Push renderer stderr/stdout to Grafana Cloud Loki (via the OTLP logs
    pipeline) so LogsAgent has real log lines to search — including genuine
    Blender error output when break_texture is active.
    """
    message = stderr.strip() or "render ok"
    _logger.info(message, extra={"job_id": job_id, "frame": frame, "condition": condition})
    print(f"[logs] job={job_id} frame={frame} condition={condition} stderr={stderr[-200:] if stderr.strip() else '(none)'}")


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
