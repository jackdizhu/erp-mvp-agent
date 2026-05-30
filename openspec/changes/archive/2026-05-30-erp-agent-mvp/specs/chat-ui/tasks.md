# Chat UI — Tasks

> Spec: [specs/chat-ui/spec.md](spec.md)
> Files: `/frontend/src/ChatPage.jsx`, `/frontend/src/ApprovalCard.jsx`, `/frontend/src/App.css`

---

## 1. ChatPage 布局

- [x] 1.1 实现 ChatPage 组件 — 左侧可折叠侧栏 + 右侧聊天区域

```jsx
import { useSessionManager } from './SessionManager';
import ApprovalCard from './ApprovalCard';

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

  return (
    <div className="chat-page">
      {sidebarOpen && (
        <div className="sidebar">
          <button onClick={handleNewSession}>+ 新建会话</button>
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
          <button onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
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
```

## 2. MessageBubble 消息渲染

- [x] 2.1 实现 MessageBubble 组件 — 区分 user/assistant 样式，渲染 tool_calls 和审批卡片

```jsx
function MessageBubble({ message, messageIndex, activeSession, updateSessions, setLoading }) {
  const isUser = message.role === "user";

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

      {!isUser && message.pendingActions?.map((pa, i) => {
        const state = message.approvalStates?.find(s => s.actionId === pa.id);
        return (
          <ApprovalCard
            key={pa.id}
            pendingAction={pa}
            approvalState={state}
            onConfirm={() => handleConfirm(pa.id, true, messageIndex)}
            onReject={() => handleConfirm(pa.id, false, messageIndex)}
          />
        );
      })}
    </div>
  );
}
```

## 3. 发送消息与 API 集成

- [x] 3.1 实现 handleSend — POST /chat 集成
- [x] 3.2 实现 handleConfirm — POST /chat/confirm 集成

```jsx
const API_BASE = "http://localhost:8000";

async function handleSend() {
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
}

async function handleConfirm(actionId, approved, messageIndex) {
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
      const session = prev.find(s => s.id === activeId);
      if (session) {
        updateApprovalState(session, messageIndex, actionId,
          approved ? (data.error ? "failed" : "success") : "rejected",
          data
        );
        if (data.reply) {
          session.messages.push(createMessage("assistant", data.reply, data.tool_calls, null));
        }
      }
      return [...prev];
    });
  } catch (e) {
    updateSessions(prev => {
      const session = prev.find(s => s.id === activeId);
      if (session) {
        updateApprovalState(session, messageIndex, actionId, "failed");
      }
      return [...prev];
    });
  } finally {
    setLoading(false);
  }
}
```

## 4. ApprovalCard 审批卡片组件

- [x] 4.1 实现 ApprovalCard 组件 — 6 种状态渲染
- [x] 4.2 实现卡片视觉样式
- [x] 4.3 实现确认/取消按钮
- [x] 4.4 实现不可逆操作警告
- [x] 4.5 实现多卡片独立渲染

```jsx
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
  const status = approvalState?.status || "pending";
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
  const detail = pendingAction.detail || {};
  const fields = detail.fields || [];
  const isPending = status === "pending";

  return (
    <div className="approval-card" style={style}>
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
          <button className="confirm-btn" onClick={onConfirm}>✅ 确认执行</button>
          <button className="cancel-btn" onClick={onReject}>❌ 取消操作</button>
        </div>
      )}
    </div>
  );
}
```

## 5. CSS 样式

- [x] 5.1 实现整体布局样式
- [x] 5.2 实现消息气泡样式
- [x] 5.3 实现审批卡片样式
- [x] 5.4 实现侧栏样式

```css
.chat-page {
  display: flex;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.sidebar {
  width: 260px;
  background: #f8f9fa;
  border-right: 1px solid #dee2e6;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.session-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.session-item:hover { background: #e9ecef; }
.session-item.active { background: #dbeafe; }

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message.user .message-content {
  background: #007bff;
  color: white;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 16px;
  margin-left: auto;
  max-width: 70%;
  display: inline-block;
}

.message.assistant .message-content {
  background: #f1f3f5;
  border-radius: 16px 16px 16px 4px;
  padding: 10px 16px;
  max-width: 70%;
  display: inline-block;
}

.approval-card {
  margin-top: 8px;
  border-radius: 12px;
  padding: 16px;
  max-width: 400px;
}

.approval-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.risk-badge.danger {
  background: #fee;
  color: #c0392b;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.field-row {
  display: flex;
  padding: 4px 0;
  font-size: 14px;
}
.field-name { color: #666; width: 80px; flex-shrink: 0; }
.field-value { color: #333; font-weight: 500; }

.irreversible-warning {
  color: #c0392b;
  font-size: 13px;
  margin: 8px 0;
  padding: 6px 10px;
  background: #fee;
  border-radius: 6px;
}

.approval-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.confirm-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}
.cancel-btn {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.input-area {
  padding: 12px 16px;
  border-top: 1px solid #dee2e6;
  display: flex;
  gap: 8px;
}

.input-hint {
  color: #e67e22;
  font-size: 13px;
  margin-bottom: 4px;
}

.input-area input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
}

.input-area input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}
```
