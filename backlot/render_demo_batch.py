"""Render the demo job's real frame batch: a contiguous range of the film
rendered under the low_samples fault, so the Demo Mode recording is grounded
in a real range of genuinely defective frames rather than one frame copied
around.

This matters for honesty, not just polish: a bad Cycles sample-count setting
on a render job affects every frame that job renders, not one. The impact
math ("N frames must be re-rendered") is only credible if N real defective
frames actually exist.

Usage:
    python backlot/render_demo_batch.py
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLEND_FILE = REPO_ROOT / "backlot" / "assets" / "movie.blend"
OUT_DIR = REPO_ROOT / "backlot" / "frames_local" / "job-seq042-sh0420"

# Frames 181-192 of the shot — matches fixtures/shotlist.json, where sh0420
# has 12 frames left to render (240 total, 228 done).
FIRST_FRAME = 181
LAST_FRAME = 192


def render(frame: int) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_expr = (
        "import bpy\n"
        "bpy.context.scene.render.engine = 'CYCLES'\n"
        "bpy.context.scene.cycles.samples = 1\n"
        "bpy.context.scene.cycles.use_denoising = False\n"
        "bpy.context.scene.render.resolution_x = 480\n"
        "bpy.context.scene.render.resolution_y = 240\n"
        f"bpy.context.scene.frame_set({frame})\n"
    )
    render_expr = (
        "import bpy\n"
        f"bpy.context.scene.render.filepath = '{OUT_DIR}/frame_{frame:04d}.png'\n"
        "bpy.ops.render.render(write_still=True)\n"
    )
    result = subprocess.run(
        ["blender", "--background", str(BLEND_FILE), "--python-expr", setup_expr, "--python-expr", render_expr],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"blender failed on frame {frame}: {result.stderr[-2000:]}")


def main() -> None:
    if not BLEND_FILE.exists():
        raise FileNotFoundError(f"{BLEND_FILE} not found — see backlot/assets/README.md")
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    for frame in range(FIRST_FRAME, LAST_FRAME + 1):
        print(f"rendering frame {frame} (low_samples)...")
        render(frame)
    print(f"\nrendered {LAST_FRAME - FIRST_FRAME + 1} real defective frames -> {OUT_DIR}")


if __name__ == "__main__":
    main()
