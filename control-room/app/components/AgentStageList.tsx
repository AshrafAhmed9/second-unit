import type { Stage } from "../types";

const STAGE_LABELS: Record<string, string> = {
  TriageAgent: "Triage",
  MetricsAgent: "Metrics (Prometheus)",
  LogsAgent: "Logs (Loki)",
  TraceAgent: "Traces (Tempo)",
  EyesAgent: "Vision — checking the picture",
  SkepticAgent: "Verify — skeptic",
  ReexamineAgent: "Verify — re-examine",
  VerdictAgent: "Verdict",
  ImpactAgent: "Impact — deadline & cost",
  PlannerAgent: "Plan",
  ActuatorAgent: "Write-back to Grafana",
};

// The one place a real broken frame belongs inline with the agent trail —
// EyesAgent's own words are what flagged it, so the picture sits right
// under them, not off in a separate gallery the reader has to go find.
const FLAGGED_FRAME_SRC = "/frames/job-seq042-sh0420__frame_0185.png";

export function AgentStageList({ stages }: { stages: Stage[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
      {stages.map((s, i) => {
        const flagged = s.stage === "EyesAgent";
        return (
          <div
            key={i}
            style={{
              padding: "var(--space-3)",
              borderRadius: "var(--radius)",
              background: flagged ? "#1a160e" : "var(--bg-raised)",
              border: `1px solid ${flagged ? "var(--border-amber)" : "var(--border)"}`,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, color: flagged ? "var(--amber)" : "var(--text-dim)", marginBottom: 4 }}>
              {STAGE_LABELS[s.stage] ?? s.stage}
            </div>
            <div style={{ fontSize: 14, color: "#ced3da", whiteSpace: "pre-wrap" }}>{s.content}</div>
            {flagged && (
              <div style={{ marginTop: "var(--space-2)", maxWidth: 240, borderRadius: 6, overflow: "hidden", border: "1px solid var(--border-amber)" }}>
                <img
                  src={FLAGGED_FRAME_SRC}
                  alt="The real defective frame EyesAgent flagged, obscured by dense denoiser noise"
                  width={240}
                  height={135}
                  style={{ width: "100%", display: "block", imageRendering: "pixelated" }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
