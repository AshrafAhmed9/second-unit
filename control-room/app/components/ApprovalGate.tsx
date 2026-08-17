"use client";

export function ApprovalGate({
  plan,
  disabled,
  onApprove,
  onReject,
}: {
  plan: string;
  disabled: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div style={{ padding: 16, borderRadius: 8, background: "#12151a", border: "1px solid #2a2f37" }}>
      <div style={{ fontSize: 12, color: "#9aa4b2", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
        Proposed plan — nothing writes to Grafana until you approve
      </div>
      <div style={{ fontSize: 14, marginBottom: 14 }}>{plan}</div>
      <div style={{ display: "flex", gap: 10 }}>
        <button
          disabled={disabled}
          onClick={onApprove}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "1px solid #2f6b3a",
            background: disabled ? "#1a1d22" : "#193d20",
            color: disabled ? "#5a6270" : "#8fe29a",
            cursor: disabled ? "not-allowed" : "pointer",
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
            border: "1px solid #3a3f47",
            background: "transparent",
            color: "#c3c9d1",
            cursor: disabled ? "not-allowed" : "pointer",
          }}
        >
          Reject
        </button>
      </div>
    </div>
  );
}
