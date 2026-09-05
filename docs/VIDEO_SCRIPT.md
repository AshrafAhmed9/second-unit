# SECOND UNIT — demo video script (target 2:55)

Three separate tracks, kept deliberately distinct:
- **ON SCREEN:** what the recording shows.
- **SAY:** your spoken narration.
- **CAPTION:** short burned-in text overlay (lower-third or on-screen
  label). Never a transcript of SAY: it either labels what's on screen or
  surfaces a number the voiceover doesn't say aloud, so a muted viewer gets
  different, complementary information rather than subtitles.

## 0:00–0:07 — Cold open, no logo, no intro card

**ON SCREEN:** Full-screen Grafana Cloud dashboard already up, "SECOND UNIT —
Render Farm Ops Wall." CPU-utilization panel green, no active alerts,
dashboard sitting there quietly for the full 7 seconds.

**SAY:**
> "This dashboard says everything is fine."

**CAPTION:** `No active alerts.`

Say it flat, not dramatic. Let the boring green graph sit on screen doing
nothing — that's the point.

## 0:07–0:15 — The cut

**ON SCREEN:** Hard cut to the actual rendered frame — the panther shot
buried in denoiser fireflies. No transition effect, just cut.

**SAY:**
> "It isn't."

**CAPTION:** `Green metrics. Broken art.`

This is your title card, delivered as text while the voice says something
shorter. Don't say the caption out loud — let it land as its own beat.

## 0:15–0:28 — Who cares, and why now

**ON SCREEN:** Control room UI, dailies countdown visible, ticking down
toward the client review deadline.

**SAY:**
> "Render farms are the biggest cost in animation and VFX pipelines. When a
> shot comes out broken like this, nobody catches it until dailies the next
> morning. Hours too late."

**CAPTION:** `Next dailies screening: 2h 14m`

Caption shows the live countdown number, not a repeat of the sentence.

## 0:28–0:40 — What this actually is

**ON SCREEN:** Stay on control room. Cursor hovers over the agent crew list
(Triage, Evidence, Verify, Impact, Plan) without clicking yet.

**SAY:**
> "SECOND UNIT watches the farm the way Grafana does. It also looks at the
> frames themselves, because nothing else in the pipeline actually does."

**CAPTION:** `Triage → Evidence → Verify → Impact → Plan → Approve → Write-back`

The agent pipeline named in one line — information the voiceover doesn't
spell out.

## 0:40–0:55 — Kick off the real run

**ON SCREEN:** Click into Live Mode (or start the recorded run if the stack's
asleep on record day — see note below). TriageAgent's line streams in.

**SAY:**
> "Here it is, running live."

**CAPTION:** `job-seq042-sh0420 · 12 frames remaining`

Then go quiet and let the agent output stream on screen for the next
segment — don't narrate over every line. Let it breathe.

## 0:55–1:25 — Evidence agents stream in (mostly silent, agent text carries it)

**ON SCREEN:** Let these stream naturally, in order, full text visible long
enough to read:
- LogsAgent: *"appears clean; no retry storms, OOM kills, or asset errors"*
- MetricsAgent: *"CPU utilization... between 48% and 67%. Considered green"*
- TraceAgent: *"20 render spans... no orphaned/retried spans"*
- EyesAgent: *"almost entirely obscured by denoiser noise... not clean"*

The agents' own on-screen text is doing the work here — no separate caption
needed on top of it, that would be redundant with what's already readable.

**SAY (one line only, timed to land as EyesAgent's text appears):**
> "Three agents just said this job is healthy. One of them actually looked
> at the picture."

## 1:25–1:40 — The skeptic

**ON SCREEN:** SkepticAgent's "CONFIRMED" appears.

**SAY:**
> "Before this goes anywhere, a second pass challenges the finding, so a
> stray shadow doesn't turn into a false alarm."

**CAPTION:** `Verify loop: cuts false positives before anything ships`

## 1:40–1:55 — Approve

**ON SCREEN:** ImpactAgent and PlannerAgent lines land. Cursor moves to the
Approve button, clicks it.

**SAY:**
> "A human still approves before anything gets written back."

**CAPTION:** `Nothing writes back without a human click.`

## 1:55–2:15 — The write-back, live in Grafana

**ON SCREEN:** Cut to the actual Grafana Cloud UI, showing the new
annotation appearing on the dashboard timeline in real time (or the
annotation ID confirmation on screen). This is the shot that proves the
write-back is real, not a claim.

**SAY:**
> "That approval writes straight back into Grafana. Watch. The annotation
> lands right there."

**CAPTION:** `Annotation #10 · written live via Grafana MCP`

## 2:15–2:30 — The cost, in plain numbers

**ON SCREEN:** Impact headline on screen, full text visible: "8 frames must
be re-rendered — projected finish slips past the client-review deadline,
~$142 in overtime exposure."

**SAY:**
> "Eight frames, caught mid-render instead of at nine a.m. tomorrow."

**CAPTION:** `$2 re-render now vs. $142 overtime exposure tomorrow`

Let the voiceover make the point in one sentence; let the caption carry the
actual math so it's legible even paused.

## 2:30–2:45 — The scorecard

**ON SCREEN:** Full-screen the scorecard panel — lead number first: "6
defects the baseline missed."

**SAY:**
> "This isn't a one-off catch. Every one of these is an actual render,
> scored against a threshold-alerting baseline."

**CAPTION:** `6 defects the metrics-only baseline missed entirely`

Use whatever the freshly regenerated numbers say once the demo recording is
resynced — detection rate, false-positive rate, and the "6" should all match
`eval/RESULTS.md` exactly. As of the last harness run: 100% detection, 0%
false positives, 6 defects caught. The live demo currently still shows a
stale 25% false-positive number until the Grafana stack is woken and the
recording is recaptured.

## 2:45–2:53 — The practitioner quote

**ON SCREEN:** Full-screen text card, the person's name and role, quote in
large text.

**SAY:** Nothing — let it sit in silence for the read time, no voiceover
competing with it.

**CAPTION:** The quote itself, verbatim, once you have it, with the person's
name and role underneath — this is the one beat where the caption legitimately
IS the entire content, since there's no separate narration to differ from.

## 2:53–3:00 — Stack card and out

**ON SCREEN:** Simple text card, then the hosted URL.

**SAY:**
> "SECOND UNIT. Built on Gemini and Grafana."

**CAPTION:** `Gemini · Google ADK · Cloud Run · Grafana Cloud MCP (read + write) · Apache-2.0`

---

## Notes before you shoot

- **Read every line out loud before you shoot, not just off the page.**
  The first draft of this leaned on the word "real" in almost every line
  ("real run," "real render," "real annotation," "real dashboard") — that
  reads fine as bullet points but sounds like a talking point on repeat when
  spoken back to back. Fixed in this version, but if you adjust any line,
  say it out loud once and check you're not doing the same thing with a
  different word.
- **Captions are not subtitles.** Every caption above says something the
  voiceover doesn't — a live number, a label, a fact — so a viewer watching
  muted gets a genuinely different (and still complete) read of the project
  than someone only listening. Don't caption your own sentences verbatim.
- **Don't over-narrate the middle.** A judge reading real agent output on
  screen is more convincing than you summarizing it. The one spoken line in
  the 0:55–1:25 block is the only narration in that whole segment.
- **The 0:00–0:15 hook is the whole game.** Re-shoot it until "green
  metrics, broken art" lands with zero setup needed. If you're explaining
  the joke, it's not landing.
- **Wake the Grafana stack immediately before recording**
  (`https://noblesunflower3144.grafana.net`), and don't record the
  write-back shot until you've confirmed the annotation actually appears —
  don't fake that beat.
- **Sync the demo recording before the final take.** Once the stack is
  awake, recapture `agent/demo_mode/recorded_run.json` and redeploy so the
  on-screen scorecard matches the real 0% false-positive number instead of
  the stale 25% currently baked into the deployed recording.
