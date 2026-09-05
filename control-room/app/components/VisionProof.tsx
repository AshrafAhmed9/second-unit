import { FramePanel } from "./FramePanel";
import framesData from "../data/frame_proof.json";

type ProofEntry = {
  condition_id: string;
  label: "clean" | "defective";
  frame: string;
  has_defect: boolean;
  reasoning: string;
};

const proofs = framesData as ProofEntry[];

/** The strongest available evidence that this isn't a scripted demo: the
 * identical EyesAgent -> VerdictAgent pipeline, run against a genuinely
 * clean render and a genuinely defective one (captured by
 * agent/scripts/capture_frame_proof.py, verbatim, not paraphrased), landing
 * on opposite verdicts. Same agent, different input, different answer —
 * which is what a practitioner testimonial would otherwise be standing in
 * for, and this is checkable instead of testimony.
 */
export function VisionProof() {
  return (
    <section style={{ marginTop: "var(--space-6)" }}>
      <h2 style={{ fontSize: 20, fontWeight: 650, margin: "0 0 4px" }}>Same agent, different input</h2>
      <p style={{ color: "var(--text-dim)", fontSize: 14, margin: "0 0 var(--space-3)" }}>
        Two real renders, the identical vision pipeline, run once and recorded verbatim.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }} className="proof-grid">
        {proofs.map((p) => (
          <div key={p.condition_id} style={{ borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)" }}>
            <FramePanel
              src={`/frames/${p.frame}`}
              alt={p.label === "clean" ? "A genuinely clean render with sharp fur detail" : "A defective render obscured by dense denoiser noise"}
            />
            <div style={{ padding: "var(--space-3)", background: "var(--bg-raised)" }}>
              <div style={{ fontSize: 12, fontFamily: "var(--mono)", color: p.has_defect ? "var(--red)" : "var(--green)" }}>
                has_defect: {String(p.has_defect)}
              </div>
              <p style={{ fontSize: 13, color: "var(--text-dim)", margin: "4px 0 0" }}>&ldquo;{p.reasoning}&rdquo;</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
