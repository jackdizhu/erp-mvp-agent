import { useState } from 'react';

const STATUS_STYLES = {
  pending:   { border: "2px solid #e74c3c", bg: "#fff5f5" },
  executing: { border: "2px solid #f39c12", bg: "#fffaf0" },
  success:   { border: "2px solid #27ae60", bg: "#f0fff4" },
  failed:    { border: "2px solid #e74c3c", bg: "#fff5f5" },
  rejected:  { border: "2px solid #95a5a6", bg: "#f5f5f5" },
  expired:   { border: "2px solid #95a5a6", bg: "#f5f5f5" }
};

const STATUS_LABELS = {
  pending: "待确认",
  executing: "执行中...",
  success: "执行成功",
  failed: "执行失败",
  rejected: "已取消",
  expired: "已过期"
};

function ApprovalCard({ pendingAction, approvalState, onConfirm, onReject }) {
  const [actionLoading, setActionLoading] = useState(null);
  const status = approvalState?.status || "pending";
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
  const detail = pendingAction.detail || {};
  const fields = detail.fields || [];
  const isPending = status === "pending";

  const handleConfirm = () => {
    if (actionLoading) return;
    setActionLoading("confirm");
    onConfirm();
  };

  const handleReject = () => {
    if (actionLoading) return;
    setActionLoading("reject");
    onReject();
  };

  return (
    <div className="approval-card" style={{ border: style.border, background: style.bg }}>
      <div className="approval-header">
        <span className="risk-badge danger">🔴 高风险</span>
        <span className="approval-status">{STATUS_LABELS[status]}</span>
      </div>

      <div className="approval-fields">
        {fields.map((f, i) => (
          <div key={i} className="field-row">
            <span className="field-name">{f.name}</span>
            <span className="field-value">{f.value}</span>
          </div>
        ))}
      </div>

      {detail.irreversible && isPending && (
        <div className="irreversible-warning">⚠️ 此操作不可撤销</div>
      )}

      {status === "success" && approvalState?.result && (
        <div className="approval-result">
          {approvalState.result.reply}
        </div>
      )}

      {status === "failed" && approvalState?.result?.error && (
        <div className="approval-error">
          {approvalState.result.error.message || "执行失败"}
        </div>
      )}

      {isPending && (
        <div className="approval-actions">
          <button
            className="confirm-btn"
            onClick={handleConfirm}
            disabled={!!actionLoading}
          >
            {actionLoading === "confirm" ? "⏳ 执行中..." : "✅ 确认执行"}
          </button>
          <button
            className="cancel-btn"
            onClick={handleReject}
            disabled={!!actionLoading}
          >
            {actionLoading === "reject" ? "⏳ 处理中..." : "❌ 取消操作"}
          </button>
        </div>
      )}
    </div>
  );
}

export default ApprovalCard;
