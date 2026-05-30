import { useState } from 'react';
import { useSessionManager, createMessage, addAssistantMessage, updateApprovalState, autoTitle, truncateHistory } from './SessionManager';
import ApprovalCard from './ApprovalCard';

const API_BASE = "http://localhost:8000";

function MessageBubble({ message, messageIndex, activeSession, updateSessions, setLoading }) {
  const isUser = message.role === "user";

  const handleConfirm = async (actionId, approved) => {
    setLoading(true);
    try {
      const history = truncateHistory(activeSession.messages);
      const res = await fetch(`${API_BASE}/chat/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: actionId, approved, history })
      });
      const data = await res.json();

      updateSessions(prev => {
        const session = prev.find(s => s.id === activeSession.id);
        if (session) {
          updateApprovalState(session, messageIndex, actionId,
            approved ? (data.error ? "failed" : "success") : "rejected",
            data
          );
          if (data.reply) {
            addAssistantMessage(session, data.reply, data.tool_calls || [], null);
          }
        }
        return [...prev];
      });
    } catch (e) {
      updateSessions(prev => {
        const session = prev.find(s => s.id === activeSession.id);
        if (session) {
          updateApprovalState(session, messageIndex, actionId, "failed");
        }
        return [...prev];
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="message-content">{message.content}</div>

      {!isUser && message.toolCalls?.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((tc, i) => (
            <div key={i} className="tool-call-item">
              <span className="tool-name">{tc.tool}</span>
              <span className="tool-args">{JSON.stringify(tc.args)}</span>
              {tc.result && (
                <span className="tool-result">→ {JSON.stringify(tc.result).slice(0, 100)}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {!isUser && message.pendingActions?.map((pa) => {
        const state = message.approvalStates?.find(s => s.actionId === pa.id);
        return (
          <ApprovalCard
            key={pa.id}
            pendingAction={pa}
            approvalState={state}
            onConfirm={() => handleConfirm(pa.id, true)}
            onReject={() => handleConfirm(pa.id, false)}
          />
        );
      })}
    </div>
  );
}

export default function ChatPage() {
  const {
    sessions, activeSession, activeId,
    handleNewSession, handleSwitchSession, handleDeleteSession,
    updateSessions
  } = useSessionManager();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const hasPendingApproval = activeSession?.messages?.some(m =>
    m.approvalStates?.some(s => s.status === "pending")
  );

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    updateSessions(prev => {
      const session = prev.find(s => s.id === activeId);
      if (session) {
        session.title = autoTitle(session, userMsg);
        session.messages.push(createMessage("user", userMsg));
      }
      return [...prev];
    });

    try {
      const history = truncateHistory(activeSession.messages);
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, history })
      });
      const data = await res.json();

      updateSessions(prev => {
        const session = prev.find(s => s.id === activeId);
        if (session) {
          addAssistantMessage(session, data.reply, data.tool_calls, data.pending_action);
        }
        return [...prev];
      });
    } catch (e) {
      updateSessions(prev => {
        const session = prev.find(s => s.id === activeId);
        if (session) {
          session.messages.push(createMessage("assistant", "请求失败，请稍后重试"));
        }
        return [...prev];
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-page">
      {sidebarOpen && (
        <div className="sidebar">
          <button className="new-session-btn" onClick={handleNewSession}>+ 新建会话</button>
          <div className="session-list">
            {sessions.map(s => (
              <div
                key={s.id}
                className={`session-item ${s.id === activeId ? "active" : ""}`}
                onClick={() => handleSwitchSession(s.id)}
              >
                <span className="session-title">{s.title}</span>
                <button
                  className="delete-btn"
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                >×</button>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="chat-area">
        <div className="chat-header">
          <button className="toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <span>ERP Agent Chat</span>
        </div>
        <div className="message-list">
          {activeSession?.messages?.map((msg, idx) => (
            <MessageBubble
              key={idx}
              message={msg}
              messageIndex={idx}
              activeSession={activeSession}
              updateSessions={updateSessions}
              setLoading={setLoading}
            />
          ))}
        </div>
        <div className="input-area">
          {hasPendingApproval && (
            <div className="input-hint">请先处理待确认操作</div>
          )}
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            disabled={loading || hasPendingApproval}
            placeholder={hasPendingApproval ? "请先处理待确认操作" : "输入消息..."}
          />
          <button onClick={handleSend} disabled={loading || hasPendingApproval}>
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
