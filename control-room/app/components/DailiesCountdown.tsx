"use client";
import { useEffect, useState } from "react";

/** The dailies countdown — the single UI element that makes the stakes
 * legible without any domain knowledge. A judge understands a clock and a
 * deadline in half a second; "render farm telemetry" takes longer.
 */
export function DailiesCountdown({ dueAt }: { dueAt: string }) {
  const [remaining, setRemaining] = useState("");

  useEffect(() => {
    const tick = () => {
      const diffMs = new Date(dueAt).getTime() - Date.now();
      if (diffMs <= 0) {
        setRemaining("PAST DUE");
        return;
      }
      const h = Math.floor(diffMs / 3_600_000);
      const m = Math.floor((diffMs % 3_600_000) / 60_000);
      const s = Math.floor((diffMs % 60_000) / 1000);
      setRemaining(`${h}h ${m}m ${s}s`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [dueAt]);

  const late = remaining === "PAST DUE";

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        padding: "var(--space-3)",
        borderRadius: "var(--radius)",
        background: late ? "#2a1414" : "var(--bg-raised)",
        border: `1px solid ${late ? "var(--border-red)" : "var(--border)"}`,
      }}
    >
      <div style={{ fontSize: 13, color: "var(--text-dim)" }}>Next dailies screening</div>
      <div style={{ fontSize: 28, fontWeight: 650, color: late ? "var(--red)" : "var(--text)", fontVariantNumeric: "tabular-nums" }}>
        {remaining || "--"}
      </div>
    </div>
  );
}
