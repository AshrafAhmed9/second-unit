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
      style={{
        padding: "12px 20px",
        borderRadius: 8,
        background: late ? "#3a1414" : "#12151a",
        border: `1px solid ${late ? "#8a2f2f" : "#2a2f37"}`,
      }}
    >
      <div style={{ fontSize: 12, color: "#9aa4b2", textTransform: "uppercase", letterSpacing: 1 }}>
        Next dailies screening
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: late ? "#ff6b6b" : "#e7e9ec", fontVariantNumeric: "tabular-nums" }}>
        {remaining || "--"}
      </div>
    </div>
  );
}
