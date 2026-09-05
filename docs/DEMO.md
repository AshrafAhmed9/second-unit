# Demo video — pre-recording checklist

The actual shot-by-shot script (verbatim narration, on-screen captions,
timing) is [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md). This is just what to
confirm before hitting record.

Record as a real screen capture of the deployed control room + the deployed
Grafana Cloud stack. Not a cinematic trailer — the rules require this
explicitly.

## Before recording

1. ✅ Real film asset in place: `backlot/assets/movie.blend`, Blender's official 5.2 LTS splash
   "Panthera Spelaea" (CC-BY) — see `backlot/assets/README.md`.
2. ✅ Real `low_samples`/`break_texture`/`kill_worker`/`clean` batch rendered via
   `backlot/render_eval_conditions.py` — real fur, real fireflies, real broken textures.
3. ✅ Real eval scorecard committed (`eval/RESULTS.md`) — 11 real rendered conditions, 100%
   detection, 0% false positives, produced by `eval/harness.py` against the real agent.
4. ✅ Both services live on Cloud Run: `second-unit-agent` and `second-unit-control-room`.
5. If re-capturing: run `agent/scripts/capture_demo_mode.py`, then redeploy the agent service
   so Demo Mode on the hosted URL serves the fresh recording — and check the recording's own
   `scorecard` field matches `eval/RESULTS.md` (see `docs/DECISIONS.md` — this drifted once).
6. **Wake the Grafana stack before recording.** Free-tier stacks go idle and show
   `{"code":"Loading"}` until a human clicks through in the browser
   (`https://<your-stack>.grafana.net` → click the loading checkbox). Do this immediately
   before you hit record — it goes back to sleep from inactivity. Do it again the day judging
   opens, since the stack will be asleep by then regardless of what's shown in the video.
7. Confirm Live Mode actually completes a full run through Approve on the **hosted** control
   room (not localhost) — instance affinity and stream buffering only surface there.

## Non-negotiables

- Public on YouTube or Vimeo, English (or English subtitles).
- Real screen recording of the actual hosted project functioning, not a mockup.
- Re-record the first 15 seconds until "green metrics, broken art" lands without narration
  needed to explain it.
