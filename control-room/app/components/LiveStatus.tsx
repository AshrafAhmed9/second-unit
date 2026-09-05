"use client";
import { useEffect, useState } from "react";
import type { LiveStatus as LiveStatusValue } from "../lib/useLiveRun";

/** Elapsed-seconds readout for a live run. A cold Cloud Run instance plus
 * four parallel Gemini calls can run 60-120s with no visible output beyond
 * the streaming stage list itself — without an explicit "this is normal"
 * signal, 90 seconds of silence reads as broken, not working.
 */
export function LiveStatus({ status }: { status: LiveStatusValue }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (status !== "running" && status !== "approving") {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [status]);

  if (status !== "running" && status !== "approving") return null;

  return (
    <div role="status" aria-live="polite" style={{ fontSize: 13, color: "var(--text-dim)" }}>
      {status === "running" ? "Diagnosing" : "Writing back"} — {elapsed}s elapsed (typical run 60-120s)
    </div>
  );
}
