"use client";
import { useCallback, useRef, useState } from "react";
import { postSse } from "./sse";
import type { Stage } from "../types";

export type LiveStatus = "idle" | "running" | "awaiting_approval" | "approving" | "done" | "blocked" | "error";

/** Drives a real Live Mode run against the deployed agent service: POST
 * /runs, stream stages over SSE, POST /runs/{id}/approve on approval,
 * stream the write-back. No auto-start — the caller decides when to spend
 * real Gemini/Grafana calls.
 *
 * "blocked" covers the Grafana-asleep case (server.py's /runs returns a
 * single "system" stage and never emits awaiting_approval — free-tier
 * stacks idle out and need a human click to wake) so the UI can say that
 * plainly instead of hanging on a run that will never finish.
 */
export function useLiveRun(agentUrl: string) {
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [stages, setStages] = useState<Stage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const runIdRef = useRef<string | null>(null);

  const start = useCallback(
    async (jobId?: string) => {
      setStages([]);
      setError(null);
      setStatus("running");
      runIdRef.current = null;
      let gotAwaitingApproval = false;

      try {
        const qs = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
        for await (const evt of postSse(`${agentUrl}/runs${qs}`)) {
          const payload = JSON.parse(evt.data);
          if (evt.event === "awaiting_approval") {
            runIdRef.current = payload.run_id;
            gotAwaitingApproval = true;
            setStatus("awaiting_approval");
            continue;
          }
          if (payload.stage === "system") {
            setStatus("blocked");
            setError(payload.content);
            return;
          }
          setStages((prev) => [...prev, payload]);
        }
        if (!gotAwaitingApproval) {
          // Stream closed without ever reaching the approval gate — the
          // server-side asleep-detection stream (server.py's asleep_stream)
          // does exactly this: one system stage, then close.
          setStatus("blocked");
          setError("Live run ended without reaching approval — the Grafana stack is likely asleep.");
        }
      } catch (e) {
        setStatus("error");
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [agentUrl]
  );

  const approve = useCallback(async () => {
    if (!runIdRef.current) return;
    setStatus("approving");
    setError(null);
    try {
      for await (const evt of postSse(`${agentUrl}/runs/${runIdRef.current}/approve`)) {
        if (evt.event !== "stage") continue;
        setStages((prev) => [...prev, JSON.parse(evt.data)]);
      }
      setStatus("done");
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [agentUrl]);

  const reject = useCallback(async () => {
    if (!runIdRef.current) return;
    await fetch(`${agentUrl}/runs/${runIdRef.current}/reject`, { method: "POST" }).catch(() => {});
    runIdRef.current = null;
    setStatus("idle");
    setStages([]);
  }, [agentUrl]);

  const reset = useCallback(() => {
    runIdRef.current = null;
    setStatus("idle");
    setStages([]);
    setError(null);
  }, []);

  return { status, stages, error, runId: runIdRef.current, start, approve, reject, reset };
}
