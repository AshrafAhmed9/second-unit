# Backlot assets

## The real asset

**`movie.blend`** is Blender's official **5.2 LTS splash file, "Panthera Spelaea"**
(a cave lion), by [Joanna Kobierska](https://www.artstation.com/joanna_kobierska).
**License: CC-BY.** 141 MB, Cycles engine, 250-frame range, 343 objects, 13
real packed (embedded) textures.

Fetch the identical file:

```bash
curl -sL -A "Mozilla/5.0" -o backlot/assets/movie.blend \
  https://download.blender.org/demo/splash/blender-5.2-splash.blend
```

Verify it's the exact same asset:

```bash
shasum -a 256 backlot/assets/movie.blend
# a48599e3c1972c70c9d4b206934871d12ba58a6dcf8b25f8c68c5baa0a747082
```

(The `www.blender.org/download/...` link on the official demo-files page
redirects through a "thanks for downloading" HTML page rather than serving
the binary — use the `download.blender.org` direct path above instead, or a
plain browser download from
[blender.org/download/demo-files/](https://www.blender.org/download/demo-files/).)

## Why this one

- **Real, embedded textures** (13 packed images: eye, fur, base color, normal,
  roughness, scatter maps) — required for a genuine `break_texture` fault;
  Blender's default startup scene has none, so an earlier version of this
  project had to skip that fault entirely.
- **Cycles by default** — a genuine `low_samples` fault (sample count forced
  to 1) produces real, visible denoiser fireflies on the fur, not a no-op
  (Blender's default scene renders in EEVEE, which ignores Cycles sample
  settings entirely — also found and fixed during this project).
- **Small enough to iterate on**: ~30s/frame at 480×240, 48 samples on this
  machine, so a full eval batch (11 frames across 4 conditions) finishes in
  under 6 minutes.
- **Official, unambiguous CC-BY** — listed directly on Blender's own
  demo-files page with the license stated inline, no separate film-rights
  page to track down.

## How the faults are actually induced

See `backlot/render_eval_conditions.py` for the exact mechanism — summarized:

- `low_samples`: `bpy.context.scene.cycles.samples = 1`, denoising disabled.
- `break_texture`: every embedded texture is unpacked (`img.unpack(method='REMOVE')`)
  then repointed to a nonexistent path — unpacking first matters, since a
  still-packed image with a broken filepath renders fine from its embedded
  data regardless of the path.
- `kill_worker`: the underlying frame renders clean; the fault is a real
  SIGKILL + retry at the process level (see `backlot/dispatch.py`), not a
  visual defect.
- `clean`: no fault, default samples (48).

This directory is gitignored for the `.blend` binary itself (141 MB, too
large for the repo) — this README plus the checksum above is enough for a
judge to fetch the identical asset in one command.
