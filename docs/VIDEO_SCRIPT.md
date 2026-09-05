# SECOND UNIT — demo video script (target 2:50, cap 3:00)

Three tracks, kept deliberately distinct:
- **ON SCREEN:** what the recording shows.
- **SAY:** verbatim spoken narration.
- **CAPTION:** burned-in text overlay. Never a transcript of SAY — it
  carries a number or label the voice doesn't say, so a viewer watching
  muted gets genuinely different, complementary information.

**Setup:** two tabs only, notifications off, bookmarks hidden. **Tab 1** =
the Grafana ops-wall dashboard (`grafana/dashboards/second-unit-ops-wall.json`,
imported into your stack — Dashboards → Browse; range set to Last 6 hours).
**Tab 2** = the control room
(https://second-unit-control-room-1026707323109.us-central1.run.app). Wake
the Grafana stack 10 minutes before recording
(https://noblesunflower3144.grafana.net — click through the loading
checkbox) — free-tier stacks idle out and Live Mode will show an honest
"asleep" message instead of running if you don't.

## 0:00–0:08 — Tab 1, dashboard, green, motionless

**SAY:** "This dashboard says every render on the farm is fine."
**CAPTION:** `Grafana Cloud · no alerts firing`

Flat delivery. Let the graph sit there doing nothing.

## 0:08–0:15 — Hard cut, full screen, to frame_0185.png

**SAY:** "It isn't."
**CAPTION:** `Green metrics. Broken art.`

Don't say the caption aloud. Hold three seconds after the line. This is
the whole hook — re-record until it lands with zero explanation needed.

## 0:15–0:30 — Tab 2, countdown ticking

**SAY:** "Render farms are the biggest line item in animation and VFX. When
a shot comes out broken like that, nobody notices until the artist opens
dailies the next morning. Hours too late, and the shot has to go again."
**CAPTION:** `Next dailies screening: 2h 14m`

## 0:30–0:42 — Cursor over the agent list

**SAY:** "SECOND UNIT watches the farm the way Grafana does. It also looks
at the frames themselves, which nothing else in the pipeline does."
**CAPTION:** `Triage → Evidence → Verify → Impact → Plan → Approve → Write-back`

## 0:42–0:50 — Click Live Mode, then Start live run

**SAY:** "This is running live, not a replay."
**CAPTION:** `job-seq042-sh0420 · 12 frames remaining`

## 0:50–1:25 — Stages stream in. Silence until 1:12

On screen: LogsAgent `clean` · MetricsAgent (real result this run) ·
TraceAgent `20 spans` · EyesAgent flags the defect, **with the frame
visible in its card**.

**SAY** (at ~1:12, as the frame appears): "Three agents just called this
job healthy. The fourth one actually looked at the picture."
**CAPTION** (1:12): `3 of 4 agents: healthy · 1 of 4: looked at the frame`

Don't narrate 0:50–1:12 otherwise — the real agent output on screen is more
persuasive than commentary over it.

## 1:25–1:36 — SkepticAgent CONFIRMED

**SAY:** "A skeptic pass challenges the finding first, so a stray shadow
doesn't become a false alarm."
**CAPTION:** `Verify loop · 0% false positives across 11 real renders`

## 1:36–1:48 — Impact and Planner land. Click Approve

**SAY:** "Nothing gets written anywhere until a human approves it."
**CAPTION:** `Human approval gate`

## 1:48–2:06 — Tab 1: the annotation lands, then pan to the Tempo panel

**SAY:** "That writes back into Grafana. There's the annotation, landing on
the dashboard. And the agent's own reasoning is sitting in Tempo, so you
can debug the AI the same way you debug everything else."
**CAPTION:** `Annotation + agent traces · written live via Grafana MCP`

Record this live — don't reuse an older annotation. If it fails on the
take, cut the beat rather than fake it.

## 2:06–2:20 — Pan to the defect metric panel and the alert rule

**SAY:** "And the finding becomes a normal Prometheus metric with an alert
rule on it. A failure your dashboards structurally could not see is now
something you can page on."
**CAPTION:** `second_unit_visual_defects_detected_total · alert rule provisioned`

This is the beat that turns a clever demo into a system — don't rush it.

## 2:20–2:32 — Tab 2, impact headline with the extrapolation visible

**SAY:** "Two dollars of re-render instead of a hundred and forty-two of
overtime. On one shot. A feature carries about fifteen hundred of them."
**CAPTION:** `$2 now vs $142 tomorrow · ×1,500 shots per feature`

## 2:32–2:44 — VisionProof panel, clean and broken side by side

**SAY:** "Same pipeline, two frames. Clean render in, it says clean.
Broken render in, it flags it. That's eleven renders in the scorecard,
every one scored against what threshold alerting would have caught."
**CAPTION** (2:32): `Same agent · different input · different verdict`
**CAPTION** (2:38): `6 defects the metrics-only baseline missed entirely`

## 2:44–2:50 — Stack card, then the URL

**SAY:** "SECOND UNIT. Gemini and ADK on Cloud Run, Grafana Cloud MCP read
and write. Every frame in this video is a real render."
**CAPTION:** `Gemini · ADK · Cloud Run · Grafana Cloud MCP (read + write) · Apache-2.0`

---

## Shooting notes

- **The first 15 seconds decide this.** Re-record until "green metrics,
  broken art" lands with no explanation needed.
- Do not narrate 0:50–1:12 — let the agent output carry it.
- If the live run misbehaves, fall back to Demo Mode and change one word:
  "this is a recorded run." Never present a replay as live.
- Every caption states something the voice does not. Never subtitle
  yourself.
- **Read every line out loud before shooting.** An earlier draft of this
  script leaned on the word "real" in five separate lines and it sounded
  like a talking point on repeat. It now appears once, in the closing
  line, where it earns its place. If you rewrite a line, say it aloud and
  check you haven't reintroduced the same tic with a different word.
- The dropped practitioner-quote beat is intentionally not here — the
  VisionProof section (2:32–2:44) replaces it with real evidence (two real
  verdicts on two real frames) instead of testimony that was never
  obtained.
