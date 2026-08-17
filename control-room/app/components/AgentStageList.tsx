import type { Stage } from "../types";

const STAGE_LABELS: Record<string, string> = {
  TriageAgent: "1 · Triage",
  MetricsAgent: "2 · Metrics (Prometheus)",
  LogsAgent: "2 · Logs (Loki)",
  TraceAgent: "2 · Traces (Tempo)",
  EyesAgent: "2 · Vision — checking the picture",
  SkepticAgent: "3 · Verify — skeptic",
  ReexamineAgent: "3 · Verify — re-examine",
  ImpactAgent: "4 · Impact — deadline & cost",
  PlannerAgent: "5 · Plan",
  ActuatorAgent: "7 · Write-back to Grafana",
};

export function AgentStageList({ stages }: { stages: Stage[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {stages.map((s, i) => (
        <div
          key={i}
          style={{
            padding: "10px 14px",
            borderRadius: 6,
            background: "#12151a",
            border: "1px solid #2a2f37",
            borderLeft: s.stage === "EyesAgent" ? "3px solid #f4b942" : "3px solid #2a2f37",
          }}
        >
          <div style={{ fontSize: 11, color: "#9aa4b2", textTransform: "uppercase", letterSpacing: 0.5 }}>
            {STAGE_LABELS[s.stage] ?? s.stage}
          </div>
          <div style={{ fontSize: 14, marginTop: 4, whiteSpace: "pre-wrap" }}>{s.content}</div>
        </div>
      ))}
    </div>
  );
}
