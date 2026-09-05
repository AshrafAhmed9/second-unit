# 3-minute demo video — shot list

Record as a real screen capture of the deployed control room + the deployed Grafana Cloud
stack. Not a cinematic trailer — the rules require this explicitly.

## Before recording

1. ✅ Real film asset in place: `backlot/assets/movie.blend`, Blender's official 5.2 LTS splash
   "Panthera Spelaea" (CC-BY) — see `backlot/assets/README.md`.
2. ✅ Real `low_samples`/`break_texture`/`kill_worker`/`clean` batch rendered via
   `backlot/render_eval_conditions.py` — real fur, real fireflies, real broken textures.
3. ✅ Real eval scorecard committed (`eval/RESULTS.md`) — 11 real rendered conditions, 100%
   detection, 0% false positives, produced by `eval/harness.py` against the real agent.
4. ✅ Both services live on Cloud Run: `second-unit-agent` and `second-unit-control-room`.
5. Capture a real run into `agent/demo_mode/recorded_run.json` via
   `agent/scripts/capture_demo_mode.py`, then redeploy the agent service so Demo Mode on the
   hosted URL serves this exact real run.
6. Have the practitioner quote in hand (see the plan's item A) before scripting the ending.
7. **Wake the Grafana stack before recording.** Free-tier stacks go idle and show
   `{"code":"Loading"}` until a human clicks through in the browser
   (`https://<your-stack>.grafana.net` → click the loading checkbox). If you plan to show
   Live Mode or the imported dashboard on camera, do this immediately before you hit record —
   it goes back to sleep from inactivity. Do this again the day judging opens, since the stack
   will be asleep by then regardless of what's shown in the video.

## Shot list (target: 2:55, hard cap 3:00)

| Time | Shot | Say / show |
|---|---|---|
| 0:00–0:15 | **The hook.** Grafana Cloud dashboard, all green, no active alerts. Cut to EyesAgent flagging the frame. Cut to the actual noisy fur/fireflies on the real lion render. | "Every metric on this render farm says everything is fine. It isn't." |
| 0:15–0:40 | The problem, stated as the clock and the money — dailies countdown on screen. | One sentence on why this costs real studios real money, today. |
| 0:40–1:55 | Live run in the control room: triage → evidence (metrics/logs/traces/vision) → verify loop → impact → plan. End on the human clicking Approve and the annotation/incident appearing **live in the Grafana Cloud UI**, not just in our UI. | Narrate only where it adds information; let the agent stream speak. |
| 1:55–2:20 | The impact headline and cost payoff on screen. | "$X and Yh saved by catching this before the dailies, not after." |
| 2:20–2:40 | The scorecard, on screen. | "No synthetic data — every one of these is a real render. Vision caught N defects the farm's existing alerting never would have." |
| 2:40–2:52 | The practitioner quote, on screen, named. | Let it speak for itself. |
| 2:52–3:00 | Stack card: Gemini · ADK · Cloud Run · Grafana Cloud MCP (read + write) · Apache-2.0. | End on the URL. |

## Non-negotiables

- Public on YouTube or Vimeo, English (or English subtitles).
- Real screen recording of the actual hosted project functioning, not a mockup.
- Re-record the first 15 seconds until "green metrics, broken art" lands without narration
  needed to explain it.
