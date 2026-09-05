import { FramePanel } from "./FramePanel";

/** The primary visual, not a supporting card: the same contradiction the
 * thesis line states, made visible. A green Grafana-style metrics face next
 * to the actual broken frame it produced — this pairing is the product;
 * everything else on the page is supporting detail for it.
 */
export function ContradictionHero({
  jobId,
  metricsHeadline,
  metricsSub,
  frameSrc,
  frameCaption,
}: {
  jobId: string;
  metricsHeadline: string;
  metricsSub: string;
  frameSrc: string;
  frameCaption: string;
}) {
  return (
    <section
      aria-label="The contradiction: green metrics next to the frame they produced"
      style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}
      className="contradiction-grid"
    >
      <div style={{ borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-3) var(--space-3) var(--space-2)", fontSize: 13, color: "var(--text-dim)" }}>
          <span>Grafana · {jobId}</span>
          <span style={{ color: "var(--green)", fontWeight: 600 }}>● green</span>
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", padding: "var(--space-4) var(--space-3)", background: "var(--bg-raised)" }}>
          <div style={{ fontSize: 40, fontWeight: 650, fontVariantNumeric: "tabular-nums" }}>{metricsHeadline}</div>
          <div style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 4 }}>{metricsSub}</div>
        </div>
      </div>

      <div style={{ borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-3) var(--space-3) var(--space-2)", fontSize: 13, color: "var(--text-dim)" }}>
          <span>{frameSrc.split("/").pop()}</span>
          <span style={{ color: "var(--amber)", fontWeight: 600 }}>● flagged</span>
        </div>
        <FramePanel src={frameSrc} alt="Rendered frame obscured by dense multicolored denoiser noise" caption={frameCaption} />
      </div>
    </section>
  );
}
