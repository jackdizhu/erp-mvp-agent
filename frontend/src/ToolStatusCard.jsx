import { useState } from 'react';

const STATUS_LABELS = {
  executing: "执行中",
  completed: "已完成",
  error: "错误",
  pending_approval: "等待确认"
};

const STATUS_COLORS = {
  executing: "#f59e0b",
  completed: "#10b981",
  error: "#ef4444",
  pending_approval: "#8b5cf6"
};

export default function ToolStatusCard({ tool, args, status, result }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="tool-status-card">
      <div
        className="tool-card-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="tool-icon">⚙️</span>
        <span className="tool-name">{tool}</span>
        <span
          className="tool-status-badge"
          style={{ backgroundColor: STATUS_COLORS[status] || "#6b7280" }}
        >
          {STATUS_LABELS[status] || status}
        </span>
        <span className="expand-arrow">{expanded ? "▼" : "▶"}</span>
      </div>
      {expanded && (
        <div className="tool-card-body">
          <div className="tool-section">
            <h4>参数</h4>
            <pre>{JSON.stringify(args, null, 2)}</pre>
          </div>
          {result && (
            <div className="tool-section">
              <h4>结果</h4>
              <pre>{typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
