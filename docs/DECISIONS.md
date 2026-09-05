# Decisions and mistakes

What got built, what got cut, and what broke along the way — kept here
instead of hidden in commit messages, because publishing the mistakes is
part of the argument that the eval numbers in `eval/RESULTS.md` are real.

## Cut on purpose

- **A memory agent and 5 failure-class specialists**, from an earlier
  version of the graph. Neither moved the eval scorecard or appeared
  anywhere a judge would see them — they existed because "more agents"
  felt like more sophistication, not because they solved a real sub-problem.
  Removed once that became obvious.
- **Prometheus remote-write, as the metrics transport.** Started this way
  because it's the "standard" path. Replaced with the OTLP gateway (see
  below) once the remote-write encoder turned out to be dead code anyway.
- **A single "does this frame look wrong" classifier doing double duty**
  as both the free-text finding and the structured verdict. Split into
  EyesAgent (free text, needs tools) and VerdictAgent (structured
  `has_defect: bool`, no tools) — see `verdict.py`'s docstring for why
  mixing tool-calling and strict structured output wasn't worth the risk
  this late in the build.

## Bugs found the hard way

**`_encode_remote_write_sample()` raised `NotImplementedError`.** The
original metrics path called this function and it just... raised. No real
telemetry had ever actually been pushed to Grafana, despite the write-back
code looking complete. Found during an adversarial review pass, not by a
judge — replaced the whole path with real OTLP metrics/logs/traces over one
gateway (`agent/second_unit/telemetry.py`).

**A second tracer/meter provider silently loses.** OpenTelemetry's global
tracer/meter/logger providers can only be set once per process. A
module-level `configure_tracing()` call in `telemetry.py` used to win that
race unconditionally under the default `"second-unit-agent"` name, so
`backlot/worker/render_worker.py`'s later
`configure_tracing(service_name="second-unit-backlot")` call was silently
ignored — every backlot span, metric, and log ended up mislabeled under the
agent service's name in Grafana. Fixed by deleting the auto-run and making
every real caller call `configure_tracing(service_name=...)` explicitly,
as the first (only) caller in its own process.

**A hand-rolled `traced_stage()` decorator was dead code, and unnecessary.**
Written to make agent reasoning show up as Tempo spans. Never actually
imported anywhere, and it referenced an undefined `tracer` variable — would
have crashed on first use. Turned out to be solving an already-solved
problem: `google-adk` auto-instruments every sub-agent invocation, LLM
call, and tool call into a real span tree once the global tracer provider
is configured, complete with the model's actual response text as a span
attribute. Verified live: a single diagnose run produced a 35-span trace in
Tempo, including `invoke_agent EyesAgent` with EyesAgent's real reasoning
attached. Deleted the decorator instead of "fixing" it.

**Asking the model to compute a timestamp broke tool calls.** TraceAgent's
instruction originally said "pass start as (now - 30 minutes)" and let
Gemini work that out. Tempo's API requires RFC3339 strings; the model
sometimes emitted inline Python instead of a tool call
(`MALFORMED_FUNCTION_CALL`). Fixed by computing the RFC3339 strings in
Python and handing them to the model as literal values to pass verbatim —
the model should never be doing arithmetic a program can do exactly.

**Callable ADK instructions bypass state templating.** The fix above used a
callable `instruction=` function instead of a `{{state_var}}` template
string. ADK's `canonical_instruction()` marks callables
`bypass_state_injection=True` — so a callable instruction that still writes
`{{triaged_job_id}}` gets the literal string `"triaged_job_id"`, not the
real value. Found because TraceAgent queried Tempo for a job literally
named `triaged_job_id`. Fixed by reading `ctx.state` directly inside the
callable instead of relying on templating.

**Two keyword classifiers, wrong in opposite directions.** Before
VerdictAgent existed, `eval/harness.py` scored detections with string
matching directly on `visual_evidence` text. An absence-of-"clean"-phrases
version scored a real detection ("I have found visual artifacts... noise")
as *not flagged*, because its exact wording didn't match. A
presence-of-defect-words version then scored a real negation ("there are no
visual defects... the frame is clean") as *flagged*, because "defect"
matched as a substring regardless of the "no" in front of it. Not a tuning
problem — prose parsing was the wrong tool for a question with a real
structured answer. Replaced with VerdictAgent, a small no-tools agent using
`output_schema` to produce an actual boolean.

**The verify loop invented a critique on a clean frame.** An earlier
version of `VerifyLoop` always ran its full `max_iterations` regardless of
outcome. Once the skeptic had already confirmed a finding on round 1,
rounds 2–3 had nothing real left to examine — and on one run, produced an
outright fabricated new critique ("unrealistic shadows") on a genuinely
clean render just to have something to say. Because `visual_evidence` gets
overwritten each round, that fabricated text is what the rest of the graph
saw. Found scoring the first real eval run: 3 of 3 clean/kill_worker
conditions were misread as defects. Fixed with an explicit `exit_loop` tool
call the skeptic uses once confirmed, instead of always exhausting the
loop.

**An MCP subprocess leak hung the eval harness for 11 hours.** Each
evidence agent's `tools=[read_toolset()]` spins up its own `mcp-grafana`
subprocess, and nothing in ADK closes it automatically when the
agent/session goes out of scope. Building fresh agents per eval condition
(required — an ADK agent can only have one parent) without closing these
leaked 3 new subprocesses per condition; across an 11-condition run that
piled up 30+ orphaned processes and the harness eventually stalled with a
live TCP connection and zero CPU progress. Fixed by walking the agent tree
for `MCPToolset` instances and explicitly `await`ing `.close()` on each
in a `finally` block after every condition.

**A recaptured demo recording kept a stale scorecard number.** After fixing
the false-positive rate in `eval/RESULTS.md` (25% → 0%, see below), the
committed `agent/demo_mode/recorded_run.json` still had `false_positive_rate:
0.25` baked into its own `scorecard` field — a separate value, parsed from
`eval/RESULTS.md` at capture time by `capture_demo_mode.py`, that simply
hadn't been recaptured after the fix landed. Found by literally reading the
deployed `/demo` endpoint's JSON response rather than trusting that "the
eval harness is fixed" meant every downstream copy of its output was too.

**The original 25% false-positive rate was real, not a display bug.** Two
of the seeded `clean`/`kill_worker` conditions were misread as defective —
both were the verify loop's fabricated-critique behavior above, not a flaw
in EyesAgent itself. Fixed alongside the loop-exit fix; re-ran the full
11-condition harness and got 0% for real, rather than tuning the number
down without understanding why it was high.

## What this buys

None of the above numbers are hand-edited. `eval/RESULTS.md` and
`agent/demo_mode/recorded_run.json` are both regenerated from a real run
against real Gemini and real Grafana MCP — rerun them and get the same
process, if not byte-identical output (LLM calls aren't deterministic).
