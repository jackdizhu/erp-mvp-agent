import ThinkingIndicator from './ThinkingIndicator';
import ApprovalCard from './ApprovalCard';

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

          {!thinkingState && toolEvents.length === 0 && !replyContent && (
            <ThinkingIndicator message="正在处理..." />
          )}
        </div>
      )}

      {!isUser && !isStreaming && (
        <>
          {message.errorMessage && (
            <div className="error-message-banner">
              <span className="error-icon">⚠️</span>
              <span className="error-text">{message.errorMessage}</span>
            </div>
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
        const state = approvalStates.find(s => s.actionId === pa.id);
        return (
          <ApprovalCard
            key={pa.id}
            pendingAction={pa}
            approvalState={state}
            onConfirm={() => onConfirm(pa.id, true)}
            onReject={() => onConfirm(pa.id, false)}
          />
        );
      })}
    </div>
  );
}
