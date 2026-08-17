# 3-minute demo video — shot list

Record as a real screen capture of the deployed control room + the deployed Grafana Cloud
stack. Not a cinematic trailer — the rules require this explicitly.

## Before recording

1. Run a real `low_samples` backlot render and a real agent pass against it, end to end.
2. Capture that run's stage outputs into `agent/demo_mode/recorded_run.json` (replacing the
   placeholder), so Demo Mode on the hosted URL shows this exact real run.
3. Run `python eval/harness.py --n 30` for real (not `--dry-run`) once the agent is deployed,
   commit the real `eval/RESULTS.md`.
4. Have the practitioner quote in hand (see plan item A) before scripting the ending.

## Shot list (target: 2:55, hard cap 3:00)

| Time | Shot | Say / show |
|---|---|---|
| 0:00–0:15 | **The hook.** Grafana Cloud dashboard, all green, no active alerts. Cut to EyesAgent flagging frames 1180-1194. Cut to the actual noisy frame. | "Every metric on this render farm says everything is fine. It isn't." |
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
