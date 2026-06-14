import { useState } from 'react';

const STATUS_LABELS = {
  completed: "已完成",
  failed: "失败",
  pending_approval: "等待审批"
};

const STATUS_COLORS = {
  completed: "#10b981",
  failed: "#ef4444",
  pending_approval: "#8b5cf6"
};

/**
 * SkillCard — collapsible display of a matched Skill + its workflow step history.
 *
 * Mirrors the collapsible interaction pattern of ToolStatusCard but uses
 * distinct CSS class .skill-card (purple theme) to visually distinguish
 * Skill-driven responses from raw LLM tool calls.
 */
export default function SkillCard({
  skill_name,
  category,
  description,
  tools,
  workflow_steps = [],
  correlation_id,
  failed_step_id,
  onClick
}) {
  const [expanded, setExpanded] = useState(false);

  const completed = workflow_steps.filter(s => s.status === 'completed').length;
  const failed = workflow_steps.filter(s => s.status === 'failed').length;
  const pending = workflow_steps.filter(s => s.status === 'pending_approval').length;
  const total = workflow_steps.length;

  const progressText = total > 0
    ? `${completed}/${total} 步已完成${failed > 0 ? `（${failed} 失败）` : ''}${pending > 0 ? `（${pending} 待审批）` : ''}`
    : '';

  const handleClick = (e) => {
    setExpanded(!expanded);
    if (onClick) onClick(e);
  };

  return (
    <div className="skill-card">
      <div className="skill-card-header" onClick={handleClick}>
        <span className="skill-card-icon">🎯</span>
        <span className="skill-card-title">Skill: {skill_name}</span>
        <span className="skill-category-badge">
          {category === 'preset' ? '预设' : category === 'custom' ? '自定义' : category}
        </span>
        {progressText && (
          <span className="skill-progress-text">{progressText}</span>
        )}
        <span className="expand-arrow">{expanded ? "▼" : "▶"}</span>
      </div>
      {expanded && (
        <div className="skill-card-body">
          {description && (
            <div className="skill-description">{description}</div>
          )}
          {tools && tools.length > 0 && (
            <div className="skill-tools">
              {tools.map(t => (
                <span key={t} className="skill-tool-chip">🔧 {t}</span>
              ))}
            </div>
          )}
          {workflow_steps.length > 0 ? (
            <div className="skill-step-list">
              {workflow_steps.map((step, idx) => (
                <div
                  key={`${step.step_id}-${idx}`}
                  className={`skill-step-row ${failed_step_id === step.step_id ? 'failed' : ''}`}
                >
                  <span className="skill-step-id">{step.step_id}</span>
                  <span className={`skill-step-type skill-step-type-${step.type}`}>
                    {step.type === 'tool_call' ? '🔧 tool_call' : '💬 prompt'}
                  </span>
                  {step.tool && (
                    <span className="skill-step-tool">{step.tool}</span>
                  )}
                  <span
                    className="skill-step-status"
                    style={{ backgroundColor: STATUS_COLORS[step.status] || '#6b7280' }}
                  >
                    {STATUS_LABELS[step.status] || step.status}
                  </span>
                  {step.elapsed_ms != null && (
                    <span className="skill-step-elapsed">
                      {step.elapsed_ms < 1000
                        ? `${step.elapsed_ms}ms`
                        : `${(step.elapsed_ms / 1000).toFixed(1)}s`}
                    </span>
                  )}
                  {step.result_summary && (
                    <span className="skill-step-result">→ {step.result_summary}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="skill-empty-steps">无工作流步骤</div>
          )}
          {correlation_id && (
            <div
              className="skill-correlation-id"
              title="Skill 执行追踪 ID，可在日志中按此 ID 检索完整事件链"
            >
              🔗 {correlation_id}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
