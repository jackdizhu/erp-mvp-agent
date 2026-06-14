import ThinkingIndicator from './ThinkingIndicator';
import ApprovalCard from './ApprovalCard';
import SkillCard from './SkillCard';
import SkillInfoBanner from './SkillInfoBanner';

export default function StreamingMessage({ message, messageIndex, activeSession, updateSessions, setLoading, onConfirm }) {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming === true;
  const replyContent = message.replyContent || "";
  const toolEvents = message.toolEvents || [];
  const thinkingState = message.thinkingState;
  const isDone = message.isDone === true;
  const pendingActions = message.pendingActions || [];
  const approvalStates = message.approvalStates || [];
  const completedTools = message.completedTools || [];
  // Skill observability fields (add-skill-observability)
  const skillMatched = message.skillMatched;
  const workflowSteps = message.workflowSteps || [];
  const skillFailed = message.skillFailed;
  const correlationId = message.correlationId;
  const failedStepId = skillFailed?.failed_step_id;

  // Banner mutual exclusion: failure > need_more_info > info
  const showFailureBanner = !!skillFailed;
  const showInfoBanner = !showFailureBanner && !!skillMatched;

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      {message.content && (
        <div className="message-content">{message.content}</div>
      )}

      {!isUser && isStreaming && (
        <div className="streaming-content">
          {thinkingState && (
            <ThinkingIndicator
              stage={thinkingState.stage}
              message={thinkingState.message}
            />
          )}

          {showInfoBanner && (
            <SkillInfoBanner
              skill_name={skillMatched.name}
              category={skillMatched.category}
              tools={skillMatched.tools || []}
            />
          )}

          {toolEvents.length > 0 && (
            <div className="tool-call-sequence">
              {toolEvents.map((te, idx) => (
                <div key={idx} className="tool-sequence-item">
                  <span className="tool-step-num">{idx + 1}</span>
                  <span className="tool-step-name">{te.tool}</span>
                </div>
              ))}
            </div>
          )}

          {replyContent && (
            <div className="reply-text">{replyContent}</div>
          )}

          {!thinkingState && toolEvents.length === 0 && !replyContent && !showInfoBanner && (
            <ThinkingIndicator message="正在处理..." />
          )}
        </div>
      )}

      {!isUser && !isStreaming && (
        <>
          {skillFailed && (
            <div className="error-message-banner">
              <span className="error-icon">⚠️</span>
              <span className="error-text">
                技能 {skillFailed.name} 执行失败：
                {(skillFailed.error_detail || '').slice(0, 100)}
                {(skillFailed.error_detail || '').length > 100 ? '...' : ''}
                （错误码：{skillFailed.error_code}）
                {skillFailed.error_code === 'SKILL_EXECUTION_FAILED' && '（可重试或换种方式描述）'}
              </span>
            </div>
          )}

          {showInfoBanner && (
            <SkillInfoBanner
              skill_name={skillMatched.name}
              category={skillMatched.category}
              tools={skillMatched.tools || []}
            />
          )}

          {skillMatched && (
            <SkillCard
              skill_name={skillMatched.name}
              category={skillMatched.category}
              description={skillMatched.description}
              tools={skillMatched.tools || []}
              workflow_steps={workflowSteps}
              correlation_id={correlationId}
              failed_step_id={failedStepId}
            />
          )}

          {completedTools.length > 0 && (
            <div className="tool-call-sequence">
              {completedTools.map((tc, i) => (
                <div key={i} className="tool-sequence-item">
                  <span className="tool-step-num">{i + 1}</span>
                  <span className="tool-step-name">{tc}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!isUser && pendingActions.map((pa) => {
        const state = approvalStates.find(s => s.actionId === pa.action_id);
        return (
          <ApprovalCard
            key={pa.action_id}
            pendingAction={pa}
            approvalState={state}
            onConfirm={() => onConfirm(pa.action_id, true)}
            onReject={() => onConfirm(pa.action_id, false)}
          />
        );
      })}
    </div>
  );
}
