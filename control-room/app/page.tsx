"use client";
import { useEffect, useState } from "react";
import { DailiesCountdown } from "./components/DailiesCountdown";
import { AgentStageList } from "./components/AgentStageList";
import { ScoreCard } from "./components/ScoreCard";
import { ImpactExtrapolation } from "./components/ImpactExtrapolation";
import { ApprovalGate } from "./components/ApprovalGate";
import { ContradictionHero } from "./components/ContradictionHero";
import { VisionProof } from "./components/VisionProof";
import { LiveStatus } from "./components/LiveStatus";
import { useLiveRun } from "./lib/useLiveRun";
import type { DemoRecording } from "./types";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";
const FLAGGED_FRAME_SRC = "/frames/job-seq042-sh0420__frame_0185.png";
const DEMO_DUE_OFFSET_HOURS = 2;

/** The control room. Defaults to Demo Mode — a real recorded run replayed
 * with zero API calls and zero cost — so the hosted URL works for a
 * stranger clicking it weeks after submission, after any free-trial
 * credits lapse. Live Mode triggers a real run against the deployed agent
 * service and streams it over SSE (see lib/sse.ts, lib/useLiveRun.ts).
 */
export default function ControlRoom() {
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [demo, setDemo] = useState<DemoRecording | null>(null);
  const live = useLiveRun(AGENT_URL);

  useEffect(() => {
    if (mode !== "demo") return;
    fetch(`${AGENT_URL}/demo`)
      .then((r) => r.json())
      .then(setDemo)
      .catch(() => setDemo(null));
  }, [mode]);

  useEffect(() => {
    // Prewarm the Cloud Run instance on switching to Live Mode, so the
    // ~10-20s cold start happens while the person is still reading the
    // page instead of after they click Start.
    if (mode === "live") {
      fetch(`${AGENT_URL}/status`).catch(() => {});
    }
  }, [mode]);

  const eyesFlagged = mode === "demo" ? true : live.stages.some((s) => s.stage === "EyesAgent");
  const jobId = mode === "demo" ? demo?.job_id ?? "job-seq042-sh0420" : "job-seq042-sh0420";
  // Both modes re-anchor to page-load time at the real ~2h horizon the
  // captured run had (agent/fixtures/shotlist.json's due_at="now+2h") —
  // demo.due_at is a fixed point in wall-clock time from whenever the
  // recording was captured, so using it directly (including as a Live Mode
  // fallback) would show PAST DUE weeks later. Only the agents' own
  // narrative text carries the real captured timestamps.
  const dueAt = new Date(Date.now() + DEMO_DUE_OFFSET_HOURS * 3_600_000).toISOString();

  // The hero panel must reflect what actually happened THIS run, not the
  // recorded demo's fixed number — showing "48-67%, green" in Live Mode
  // while this run's own MetricsAgent reported something different (e.g.
  // "couldn't find the metric") would be exactly the kind of claim this
  // project argues against making. Demo Mode uses the one real captured
  // number; Live Mode surfaces MetricsAgent's own text for this run,
  // verbatim, or an honest "watching" placeholder before it lands.
  const liveMetricsContent = live.stages.find((s) => s.stage === "MetricsAgent")?.content;
  const metricsHeadline = mode === "demo" ? "48–67%" : liveMetricsContent ? "this run" : "watching…";
  const metricsSub =
    mode === "demo"
      ? "CPU utilization, worker pool — 30m window, no alerts firing"
      : liveMetricsContent ?? "MetricsAgent hasn't reported yet";

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "var(--space-5) var(--space-4) var(--space-6)" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "var(--space-5)", gap: "var(--space-4)", flexWrap: "wrap" }}>
        <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: "0.02em" }}>
          SECOND UNIT <span style={{ color: "var(--text-faint)", fontWeight: 400 }}>· render farm ops</span>
        </div>
        <div role="group" aria-label="Mode" style={{ display: "flex", gap: 2, background: "var(--bg-raised)", border: "1px solid var(--border)", borderRadius: 8, padding: 2 }}>
          <ModeButton active={mode === "demo"} onClick={() => setMode("demo")} label="Demo" />
          <ModeButton active={mode === "live"} onClick={() => setMode("live")} label="Live" />
        </div>
      </header>

      <h1 style={{ fontSize: 34, fontWeight: 650, letterSpacing: "-0.015em", lineHeight: 1.15, maxWidth: 760, margin: "0 0 var(--space-5)" }}>
        Every metric on this job says <span style={{ color: "var(--amber)" }}>fine</span>. The frame it produced doesn&rsquo;t.
      </h1>

      {mode === "demo" && !demo && (
        <p style={{ color: "var(--text-dim)" }}>
          Loading recorded run… (see docs/DEMO.md — capture one with the agent service running and GET
          /demo will serve it from second-unit/agent/demo_mode/recorded_run.json)
        </p>
      )}

      {mode === "live" && live.status === "idle" && (
        <div style={{ marginBottom: "var(--space-5)" }}>
          <button
            onClick={() => live.start()}
            style={{
              padding: "10px 20px",
              borderRadius: 8,
              border: "1px solid var(--border-green)",
              background: "#193d20",
              color: "var(--green)",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Start live run
          </button>
          <p style={{ color: "var(--text-faint)", fontSize: 13, marginTop: 8 }}>
            Real Gemini + real Grafana MCP calls against the deployed agent service. Typically 60-120s.
          </p>
        </div>
      )}

      {mode === "live" && live.status === "blocked" && (
        <div style={{ padding: "var(--space-3)", borderRadius: "var(--radius)", background: "#2a1414", border: "1px solid var(--border-red)", marginBottom: "var(--space-5)" }}>
          <p style={{ margin: 0, fontSize: 14 }}>{live.error ?? "Live Mode can't reach the Grafana stack right now."}</p>
          <button
            onClick={() => setMode("demo")}
            style={{ marginTop: 10, padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--text-dim)", cursor: "pointer" }}
          >
            Switch to Demo Mode
          </button>
        </div>
      )}

      {mode === "live" && live.status === "error" && (
        <p style={{ color: "var(--red)" }}>{live.error ?? "Live run failed."}</p>
      )}

      {((mode === "demo" && demo) || (mode === "live" && live.status !== "idle" && live.status !== "blocked")) && (
        <>
          {eyesFlagged && (
            <ContradictionHero
              jobId={jobId}
              metricsHeadline={metricsHeadline}
              metricsSub={metricsSub}
              frameSrc={FLAGGED_FRAME_SRC}
              frameCaption='EyesAgent: "critically corrupted — denoiser fireflies, subject obscured"'
            />
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "var(--space-4)", alignItems: "start" }} className="main-grid">
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: 13, color: "var(--text-dim)" }}>
                  {mode === "demo" ? `${demo?.sequence} / ${demo?.shot_id} · job ${demo?.job_id}` : `job ${jobId}`}
                </div>
                <LiveStatus status={mode === "live" ? live.status : "idle"} />
              </div>

              <AgentStageList stages={mode === "demo" ? demo!.stages : live.stages} />

              {(mode === "demo" || live.status === "awaiting_approval" || live.status === "approving" || live.status === "done") && (
                <ApprovalGate
                  plan={mode === "demo" ? demo!.plan : live.stages.find((s) => s.stage === "PlannerAgent")?.content ?? ""}
                  demoMode={mode === "demo"}
                  disabled={mode === "live" && live.status !== "awaiting_approval"}
                  onApprove={live.approve}
                  onReject={live.reject}
                />
              )}

              {mode === "demo" && (
                <div style={{ padding: "var(--space-3)", borderRadius: "var(--radius)", background: "var(--bg-raised)", border: "1px solid var(--border-green)" }}>
                  <div style={{ fontSize: 12, color: "var(--green)", textTransform: "uppercase", letterSpacing: 1 }}>Written back to Grafana (recorded)</div>
                  <div style={{ fontSize: 14, marginTop: 6 }}>{demo!.actuator_result}</div>
                </div>
              )}

              {mode === "live" && live.status === "done" && (
                <div style={{ padding: "var(--space-3)", borderRadius: "var(--radius)", background: "var(--bg-raised)", border: "1px solid var(--border-green)" }}>
                  <div style={{ fontSize: 12, color: "var(--green)", textTransform: "uppercase", letterSpacing: 1 }}>Written back to Grafana</div>
                  <div style={{ fontSize: 14, marginTop: 6 }}>{live.stages.find((s) => s.stage === "ActuatorAgent")?.content}</div>
                </div>
              )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <DailiesCountdown dueAt={dueAt} />
              <div style={{ padding: "var(--space-3)", borderRadius: "var(--radius)", background: "var(--bg-raised)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 8 }}>Impact</div>
                <div style={{ fontSize: 14 }}>
                  {mode === "demo" ? demo!.impact_headline : live.stages.find((s) => s.stage === "ImpactAgent")?.content ?? "Pending…"}
                </div>
              </div>
              {mode === "demo" && <ImpactExtrapolation />}
              {mode === "demo" && <ScoreCard scorecard={demo!.scorecard} />}
            </div>
          </div>
        </>
      )}

      <VisionProof />

      <footer style={{ marginTop: "var(--space-6)", paddingTop: "var(--space-4)", borderTop: "1px solid var(--border)", fontSize: 12, color: "var(--text-faint)" }}>
        Gemini · Google ADK · Cloud Run · Grafana Cloud MCP (read + write) · Apache-2.0
      </footer>
    </main>
  );
}

function ModeButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      style={{
        padding: "6px 14px",
        borderRadius: 6,
        fontSize: 13,
        border: "none",
        background: active ? "#1f2530" : "transparent",
        color: active ? "var(--text)" : "var(--text-dim)",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
