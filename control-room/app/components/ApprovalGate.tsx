"use client";

export function ApprovalGate({
  plan,
  demoMode,
  disabled,
  onApprove,
  onReject,
}: {
  plan: string;
  demoMode: boolean;
  disabled: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div style={{ padding: "var(--space-3)", borderRadius: "var(--radius)", background: "var(--bg-raised)", border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 8 }}>
        Proposed plan — nothing writes to Grafana until a human approves
      </div>
      <div style={{ fontSize: 14, marginBottom: 14 }}>{plan}</div>
      {demoMode ? (
        <p style={{ fontSize: 13, color: "var(--text-faint)", margin: 0 }}>
          Recorded run — approval already happened once, for real, during capture. Switch to Live Mode to approve one yourself.
        </p>
      ) : (
        <div style={{ display: "flex", gap: 10 }}>
          <button
            disabled={disabled}
            onClick={onApprove}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "1px solid var(--border-green)",
              background: disabled ? "#1a1d22" : "#193d20",
              color: disabled ? "var(--text-faint)" : "var(--green)",
              cursor: disabled ? "not-allowed" : "pointer",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            Approve → write to Grafana
          </button>
          <button
            disabled={disabled}
            onClick={onReject}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--text-dim)",
              cursor: disabled ? "not-allowed" : "pointer",
              fontSize: 14,
            }}
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
