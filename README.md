# SECOND UNIT

**Green metrics. Broken art. Only one of those two things is checking the picture.**

Built for the [Agentic Cinema: The Blockbuster Hackathon](https://agentic-cinema.devpost.com/) — **Grafana track**.

> Your render farm's dashboards say everything is fine. The job succeeded, exit code 0,
> normal duration, GPU utilization nominal. And the frame it produced is visibly ruined.
> No monitoring tool on earth can see that — because observability measures whether the
> **job** succeeded, never whether the **output** is correct. SECOND UNIT is a deterministic
> agent crew that reads your render farm's telemetry through Grafana *and* looks at the
> actual rendered picture with Gemini vision — so it catches the shot metrics swear is fine,
> tells you what it costs by tomorrow's dailies, and writes the incident back into Grafana
> the moment a human approves.

## Status

Live, not just described:

- **Agent service:** https://second-unit-agent-1026707323109.us-central1.run.app
- **Control room:** https://second-unit-control-room-1026707323109.us-central1.run.app
- **Real film asset:** Blender's official 5.2 LTS splash "Panthera Spelaea" (CC-BY) — see
  [`backlot/assets/README.md`](backlot/assets/README.md)
- **Real eval scorecard:** 100% detection, 0% false positives, 8/8 correct — see
  [`eval/RESULTS.md`](eval/RESULTS.md), reproducible with `python eval/harness.py`

## The 15-second version

Run `SECOND UNIT` against a render that finished cleanly by every metric. It still raises
a P1, because it looked at the frame and the frame is wrong. That contradiction — **a real
render, a real green dashboard, a real broken picture** — is the whole idea, and it is not
staged: see [`backlot/`](backlot/) for the actual Blender renders and real fault conditions
that produce it.

## Why this exists

Render farms are the largest single cost line in post-production. They fail constantly —
flaky nodes, silent retry storms, broken texture paths — and studios genuinely watch them
in Grafana today. But a render can complete perfectly by every operational metric and still
be visually wrong: denoiser noise from a bad sample count, a missing texture, corrupted
geometry. That failure class is invisible to metrics, logs, and traces by construction.
Today it's caught by an artist at the 9am dailies screening, hours after it could have been
caught mid-render. SECOND UNIT moves that catch earlier and attaches a real dollar cost to
ignoring it.

## Architecture

```
Control Room (Next.js, Cloud Run)
  shot timeline · dailies countdown · live agent stream · Grafana panels · approval gate
        │ SSE / REST
Agent service (Python, ADK, Cloud Run)
  SequentialAgent → ParallelAgent(evidence) → LoopAgent(verify) → Impact → Plan
  → [HUMAN APPROVAL] → ActuatorAgent (write-back)
  Gemini via Vertex / Gemini Enterprise Agent Platform
  OTel traces of its own reasoning → Grafana Tempo
        │ MCP (grafana/mcp-grafana, stdio sidecar)         │ GCS
  Grafana Cloud (Prometheus, Loki, Tempo, annotations,      frames + shotlist
  incidents) — read AND write, at runtime                   (GCS + Firestore)
        ▲
THE BACKLOT — a real render farm (Cloud Run Jobs)
  headless Blender rendering real CC-BY open-movie frames.
  Real induced faults (see backlot/conditions/) — not synthetic telemetry.
```

**Three architectural decisions, and why:**

- **MCP transport: self-hosted `grafana/mcp-grafana`, not the hosted `mcp.grafana.com`
  endpoint.** The track rules permit either. Tested the hosted one directly with a
  service-account token — `401 invalid_token` — because it's OAuth-2.1-browser-consent-only
  by design (confirmed in Grafana's own docs). A Cloud Run container has no browser to
  complete that in. The self-hosted binary authenticates unattended and exposes the same 33+
  tools, including proxied Tempo access.
- **The farm renders real frames, not simulated telemetry.** A Grafana engineer spots fake
  metrics in seconds, and the entire thesis — "green metrics, broken art" — only means
  something if the metrics really are green and the art really is broken. Every fault in
  `backlot/conditions/` is induced by a real render condition: sample count actually forced
  to 1, textures actually unpacked and repointed to a dead path, workers actually SIGKILLed.
- **The agent graph is 8 agents, not more.** Every agent earns its place by moving a number
  in `eval/RESULTS.md` or appearing in the demo — nothing was added to hit a target count.
  Complexity without a measurable purpose was cut on sight during development (an earlier
  version had 5 failure-class specialists and a memory agent; neither moved the eval numbers,
  so both were removed).

## The agent graph

| # | Agent | Does |
|---|---|---|
| 1 | TriageAgent | Picks the highest-risk render job right now |
| 2 | MetricsAgent / LogsAgent / TraceAgent | Grafana MCP → Prometheus / Loki / Tempo: is the infra healthy? |
| 2 | EyesAgent | Gemini vision on the actual frames: is the **picture** ok? |
| 3 | VerifyLoop (Skeptic → Re-examine, ≤3 rounds) | Cuts false positives — proven in `eval/RESULTS.md`, not asserted |
| 4 | ImpactAgent | Deterministic deadline/cost math (`agent/second_unit/schedule.py`, pure + unit-tested) |
| 5 | PlannerAgent | Proposes a fix, with reasoning |
| 6 | **Human approval gate** | Nothing mutates without a click |
| 7 | ActuatorAgent | Writes an incident + annotations back into Grafana |

Every agent above earns its place because removing it breaks either the eval scorecard or
the demo — see the design rationale for what was deliberately cut.

## Quickstart (no cloud credentials required)

```bash
cd second-unit
python3 -m venv .venv && source .venv/bin/activate
pip install -r agent/requirements.txt pytest

# pure logic: schedule/cost math + eval scoring, no external services
python -m pytest

# the proof — regenerate the eval scorecard
python eval/harness.py --n 30 --dry-run
cat eval/RESULTS.md
```

## Running the real thing

Requires a Google Cloud project (free trial) and a Grafana Cloud stack (permanently free
tier — see `infra/README.md` for exact setup). Zero paid services are used.

```bash
cd second-unit/infra
PROJECT_ID=your-project ./00_project_setup.sh
PROJECT_ID=your-project GRAFANA_URL=... GRAFANA_SERVICE_ACCOUNT_TOKEN=... \
  GRAFANA_CLOUD_METRICS_USER=... GRAFANA_CLOUD_METRICS_TOKEN=... \
  GRAFANA_CLOUD_LOGS_USER=... GRAFANA_CLOUD_LOGS_TOKEN=... ./01_secrets.sh
PROJECT_ID=your-project ./02_deploy_agent.sh
PROJECT_ID=your-project ./03_deploy_control_room.sh
```

Import [`grafana/dashboards/second-unit-ops-wall.json`](grafana/dashboards/second-unit-ops-wall.json)
into your own Grafana Cloud stack to see the backlot's real telemetry and the agent's
write-backs natively on your own panels.

## Path to production

What a real studio would need to change to run this for real: point `GRAFANA_URL` at their
existing stack (no schema changes — the dashboard JSON is additive), swap `agent/fixtures/shotlist.json`
for their real shot database behind the one `tools/shotlist.py` interface, and point
`backlot/` at their actual render farm's telemetry exporters instead of the demo Blender farm.
It does not replace a studio's existing alerting — it adds the one check (the picture itself)
that alerting structurally cannot perform. Estimated running cost for a mid-size farm: a
handful of Gemini vision calls per triaged job, well under Grafana Cloud's paid tier
thresholds for a single studio's telemetry volume.

## Compliance with the hackathon rules

- Grafana Cloud MCP called at runtime — `agent/second_unit/tools/grafana_mcp.py`, not just named in this README.
- Gemini + Google Cloud (Vertex/Agent Engine, Cloud Run, GCS, Firestore, Secret Manager) called at runtime.
- No non-Google AI model, agent framework, or AI API anywhere in the dependency tree (`agent/requirements.txt`).
- Apache-2.0 license at the repo root, detectable in the GitHub About section.
- Costs $0: Google Cloud free trial + hackathon credits, Grafana Cloud's permanent free tier.

## Repository layout

```
agent/         ADK agent graph, FastAPI service, unit tests
backlot/       the real render farm — worker, dispatcher, fault conditions
eval/          the proof — scoring harness + committed eval/RESULTS.md
grafana/       importable dashboard for judges' own Grafana Cloud stacks
control-room/  the product UI (Next.js)
infra/         Cloud Run deploy, Secret Manager, IAM — gcloud scripts
docs/          demo video shot list
```

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
