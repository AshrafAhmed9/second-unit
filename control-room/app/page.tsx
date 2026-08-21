"use client";
import { useEffect, useState } from "react";
import { DailiesCountdown } from "./components/DailiesCountdown";
import { AgentStageList } from "./components/AgentStageList";
import { ScoreCard } from "./components/ScoreCard";
import { ApprovalGate } from "./components/ApprovalGate";
import type { DemoRecording } from "./types";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";

// Demo Mode's recorded_run.json is a static snapshot, so its captured due_at
// is a fixed point in wall-clock time that inevitably lands in the past —
// the countdown would show "PAST DUE" forever, weeks before any judge sees
// it. Re-anchored to page-load time at the same ~2h horizon the real
// captured run actually had (see agent/fixtures/shotlist.json's
// due_at="now+2h"), so the countdown stays meaningful indefinitely. The
// agent's own narrative text (real timestamps like "0.2h past the 05:01
// deadline") is untouched — only this display widget is re-anchored.
const DEMO_DUE_OFFSET_HOURS = 2;

/**
 * The control room. Defaults to Demo Mode — a real recorded run replayed
 * with zero API calls and zero cost — so the hosted URL works for a stranger
 * clicking it weeks after submission, after any free-trial credits lapse.
 * Live Mode triggers a real run against the deployed agent service.
 */
export default function ControlRoom() {
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [demo, setDemo] = useState<DemoRecording | null>(null);
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    if (mode !== "demo") return;
    fetch(`${AGENT_URL}/demo`)
      .then((r) => r.json())
      .then(setDemo)
      .catch(() => setDemo(null));
  }, [mode]);

  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "32px 24px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>SECOND UNIT</h1>
          <p style={{ margin: "4px 0 0", color: "#9aa4b2", fontSize: 14 }}>
            Green metrics. Broken art. Only one of those two is checking the picture.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <ModeButton active={mode === "demo"} onClick={() => setMode("demo")} label="Demo Mode" />
          <ModeButton active={mode === "live"} onClick={() => setMode("live")} label="Live Mode" />
        </div>
      </header>

      {!demo && mode === "demo" && (
        <div style={{ color: "#9aa4b2" }}>
          Loading recorded run… (see docs/DEMO.md — capture one with the agent service running and
          GET /demo will serve it from second-unit/agent/demo_mode/recorded_run.json)
        </div>
      )}

      {demo && (
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: 13, color: "#c3c9d1" }}>
                {demo.sequence} / {demo.shot_id} · job {demo.job_id}
              </div>
              <DailiesCountdown
                dueAt={mode === "demo" ? new Date(Date.now() + DEMO_DUE_OFFSET_HOURS * 3_600_000).toISOString() : demo.due_at}
              />
            </div>

            <AgentStageList stages={demo.stages} />

            <ApprovalGate
              plan={demo.plan}
              disabled={mode === "demo" || approved}
              onApprove={() => setApproved(true)}
              onReject={() => setApproved(false)}
            />

            {approved && (
              <div style={{ padding: 16, borderRadius: 8, background: "#12151a", border: "1px solid #2f6b3a" }}>
                <div style={{ fontSize: 12, color: "#8fe29a", textTransform: "uppercase", letterSpacing: 1 }}>
                  Written back to Grafana
                </div>
                <div style={{ fontSize: 14, marginTop: 6 }}>{demo.actuator_result}</div>
              </div>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ padding: 16, borderRadius: 8, background: "#12151a", border: "1px solid #2a2f37" }}>
              <div style={{ fontSize: 12, color: "#9aa4b2", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                Impact
              </div>
              <div style={{ fontSize: 14 }}>{demo.impact_headline}</div>
            </div>
            <ScoreCard scorecard={demo.scorecard} />
          </div>
        </div>
      )}
    </main>
  );
}

function ModeButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        borderRadius: 6,
        fontSize: 13,
        border: `1px solid ${active ? "#4a5568" : "#2a2f37"}`,
        background: active ? "#1c2027" : "transparent",
        color: active ? "#e7e9ec" : "#9aa4b2",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
