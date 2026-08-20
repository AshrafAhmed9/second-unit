"""Render real frames for the eval harness's live conditions — one small
batch per locally-inducible fault type, using the real CC-BY film asset
(backlot/assets/movie.blend — Blender 5.2 LTS splash "Panthera Spelaea" by
Joanna Kobierska, CC-BY, downloaded from download.blender.org/demo/splash/).
Each condition gets its own job_id directory under frames_local/ so the
agent can be pointed at it directly.

starve_memory is excluded here: it needs an actual container memory cap
(Cloud Run Jobs), which doesn't exist locally yet — see
backlot/conditions/starve_memory.yaml. Add it to LOCAL_LIVE_CONDITIONS once
deployed.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAMES_ROOT = REPO_ROOT / "backlot" / "frames_local"
BLEND_FILE = REPO_ROOT / "backlot" / "assets" / "movie.blend"

# (condition, count). All 4 locally-inducible fault types now real, including
# break_texture — the earlier default-cube-scene version had to skip it
# because that scene had no textures at all to break. This asset has 13 real
# packed textures on a cave lion character.
LOCAL_LIVE_CONDITIONS = [
    ("clean", 3),
    ("low_samples", 3),
    ("break_texture", 3),
    ("kill_worker", 2),
]

FRAME = 1  # a fixed, known-good close-up camera pose; see backlot/assets/README.md


def render_movie_frame(out_dir: Path, condition: str) -> None:
    """Render one frame of the real film asset with the given fault applied.

    low_samples: force Cycles, crank samples down to 1, disable denoising
        (denoising would hide the fireflies we want genuinely visible).
    break_texture: unpack every embedded texture then repoint it to a
        nonexistent path. Unpacking first matters — a packed image with a
        broken filepath still renders fine from its embedded data, so this
        fault would be a no-op without it.
    clean / kill_worker's underlying frame: normal settings, real quality.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = 1 if condition == "low_samples" else 48

    setup_expr = (
        "import bpy\n"
        "bpy.context.scene.render.engine = 'CYCLES'\n"
        f"bpy.context.scene.cycles.samples = {samples}\n"
        "bpy.context.scene.cycles.use_denoising = False\n"
        "bpy.context.scene.render.resolution_x = 480\n"
        "bpy.context.scene.render.resolution_y = 240\n"
        f"bpy.context.scene.frame_set({FRAME})\n"
    )
    if condition == "break_texture":
        setup_expr += (
            "for img in bpy.data.images:\n"
            "    if img.packed_file is not None:\n"
            "        img.unpack(method='REMOVE')\n"
            "    img.filepath = '/nonexistent/broken_texture.png'\n"
            "    img.source = 'FILE'\n"
        )

    render_expr = (
        f"import bpy\n"
        f"bpy.context.scene.render.filepath = '{out_dir}/frame_0001.png'\n"
        f"bpy.ops.render.render(write_still=True)\n"
    )

    cmd = ["blender", "--background", str(BLEND_FILE), "--python-expr", setup_expr, "--python-expr", render_expr]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"blender render failed for {condition}: {result.stderr[-2000:]}")


def main():
    if not BLEND_FILE.exists():
        raise FileNotFoundError(f"{BLEND_FILE} not found — see backlot/assets/README.md")

    job_condition_map = {}
    n = 0
    for condition, count in LOCAL_LIVE_CONDITIONS:
        for i in range(count):
            job_id = f"eval-{condition}-{n:03d}"
            out_dir = FRAMES_ROOT / job_id
            print(f"rendering {job_id} (condition={condition})...")
            underlying_condition = "clean" if condition == "kill_worker" else condition
            render_movie_frame(out_dir, underlying_condition)
            job_condition_map[job_id] = condition
            n += 1

    import json
    (Path(__file__).resolve().parent / "eval_job_map.json").write_text(json.dumps(job_condition_map, indent=2))
    print(f"\nrendered {n} real frames across {len(LOCAL_LIVE_CONDITIONS)} conditions")
    print("job -> condition map written to backlot/eval_job_map.json")


if __name__ == "__main__":
    main()
