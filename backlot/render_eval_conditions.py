"""Render real frames for the eval harness's live conditions — one small
batch per locally-inducible fault type. Each condition gets its own job_id
directory under frames_local/ so the agent can be pointed at it directly.

starve_memory is excluded here: it needs an actual container memory cap
(Cloud Run Jobs), which doesn't exist locally yet — see
backlot/conditions/starve_memory.yaml. Add it to LOCAL_LIVE_CONDITIONS once
deployed.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAMES_ROOT = REPO_ROOT / "backlot" / "frames_local"

# (condition, count) — small batch to prove the harness for real; scale up
# by raising these counts once the real CC-BY asset replaces the default scene.
#
# break_texture is excluded here, honestly: Blender's default cube material
# has no image texture at all, so "repoint every image path" has nothing to
# break and produces zero visual difference (checked: 0/76800 differing
# pixels against a clean render). It needs the real film asset, which has
# actual textures — see backlot/assets/README.md. Do not fake this one.
LOCAL_LIVE_CONDITIONS = [
    ("clean", 3),
    ("low_samples", 3),
    ("kill_worker", 2),
]


def render_default_scene(frame_index: int, out_dir: Path, condition: str) -> None:
    """Render Blender's built-in default scene (no --blend file needed —
    `blender --background --python-expr ...` starts from the factory
    startup file automatically) with the given fault condition applied.

    Forces the Cycles render engine explicitly. Found empirically: Blender's
    default scene renders with EEVEE by default, which ignores
    `scene.cycles.samples` entirely — an earlier version set that property
    without switching engines first and produced 8 real renders that were
    pixel-identical (verified: max/mean diff of 0 across every pixel). Cycles
    is required for a real low-sample-count defect to actually appear.
    """
    import subprocess

    out_dir.mkdir(parents=True, exist_ok=True)
    samples = 1 if condition == "low_samples" else 128

    setup_expr = (
        "import bpy\n"
        "bpy.context.scene.render.engine = 'CYCLES'\n"
        f"bpy.context.scene.cycles.samples = {samples}\n"
        "bpy.context.scene.cycles.use_denoising = False\n"  # denoising would hide the fireflies we want visible
    )
    if condition == "break_texture":
        setup_expr += (
            "for img in bpy.data.images:\n"
            "    img.filepath = '/nonexistent/broken_texture.png'\n"
        )

    render_expr = (
        f"import bpy\n"
        f"bpy.context.scene.render.filepath = '{out_dir}/frame_{frame_index:04d}.png'\n"
        f"bpy.context.scene.render.resolution_x = 320\n"
        f"bpy.context.scene.render.resolution_y = 240\n"
        f"bpy.ops.render.render(write_still=True)\n"
    )

    cmd = ["blender", "--background", "--python-expr", setup_expr, "--python-expr", render_expr]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"blender render failed for {condition}: {result.stderr[-2000:]}")


def main():
    job_condition_map = {}
    n = 0
    for condition, count in LOCAL_LIVE_CONDITIONS:
        for i in range(count):
            job_id = f"eval-{condition}-{n:03d}"
            out_dir = FRAMES_ROOT / job_id
            print(f"rendering {job_id} (condition={condition})...")
            if condition == "kill_worker":
                render_default_scene(1, out_dir, "clean")
            else:
                render_default_scene(1, out_dir, condition)
            job_condition_map[job_id] = condition
            n += 1

    import json
    (Path(__file__).resolve().parent / "eval_job_map.json").write_text(json.dumps(job_condition_map, indent=2))
    print(f"\nrendered {n} real frames across {len(LOCAL_LIVE_CONDITIONS)} conditions")
    print("job -> condition map written to backlot/eval_job_map.json")


if __name__ == "__main__":
    main()
