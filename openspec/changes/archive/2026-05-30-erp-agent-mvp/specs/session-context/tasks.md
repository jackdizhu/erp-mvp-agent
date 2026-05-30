# Session Context — Tasks

> Spec: [specs/session-context/spec.md](spec.md)
> File: `/frontend/src/SessionManager.js`

---

## 1. 数据结构定义

- [x] 1.1 定义 Session 和 SessionManager 的数据结构

```javascript
const STORAGE_KEY = "erp_agent_sessions";

function createSession() {
  return {
    id: `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title: "新会话",
    createdAt: new Date().toISOString(),
    messages: []
  };
}

function createMessage(role, content, pendingActions = null) {
  return {
    role,
    content,
    timestamp: new Date().toISOString(),
    pendingActions: pendingActions || [],
    approvalStates: pendingActions
      ? pendingActions.map(pa => ({
          actionId: pa.id,
          status: "pending"
        }))
      : []
  };
}
```

## 2. localStorage 持久化

- [x] 2.1 实现 saveSessions — 每次状态变更时序列化保存
- [x] 2.2 实现 loadSessions — 页面加载时反序列化恢复

```javascript
function saveSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error("Failed to save sessions:", e);
  }
}

function loadSessions() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (data) {
      return JSON.parse(data);
    }
  } catch (e) {
    console.error("Failed to load sessions:", e);
  }
  return [createSession()];
}
```

## 3. 会话操作函数

- [x] 3.1 实现 newSession — 创建空会话并切换
- [x] 3.2 实现 switchSession — 切换活跃会话
- [x] 3.3 实现 deleteSession — 删除会话
- [x] 3.4 实现 autoTitle — 首条消息自动生成标题

```javascript
function newSession(sessions, setSessions, setActiveId) {
  const session = createSession();
  const updated = [session, ...sessions];
  setSessions(updated);
  setActiveId(session.id);
  saveSessions(updated);
  return session;
}

function switchSession(id, setActiveId) {
  setActiveId(id);
}

function deleteSession(id, sessions, setSessions, activeId, setActiveId) {
  const updated = sessions.filter(s => s.id !== id);
  if (updated.length === 0) {
    updated.push(createSession());
  }
  setSessions(updated);
  if (activeId === id) {
    setActiveId(updated[0].id);
  }
  saveSessions(updated);
}

function autoTitle(session, message) {
  if (session.messages.length === 0 || session.title !== "新会话") {
    return session.title;
  }
  return message.length > 20 ? message.slice(0, 20) + "..." : message;
}
```

## 4. 历史窗口截取

- [x] 4.1 实现 truncateHistory — 截取最近 N=6 轮

```javascript
function truncateHistory(messages, n = 6) {
  if (messages.length <= n) {
    return messages.map(m => ({ role: m.role, content: m.content }));
  }
  return messages
    .slice(-n)
    .map(m => ({ role: m.role, content: m.content }));
}
```

## 5. 审批状态持久化

- [x] 5.1 实现 pending_action 存储在消息中
- [x] 5.2 实现页面刷新后审批卡片恢复

```javascript
function addAssistantMessage(session, reply, toolCalls, pendingAction) {
  const pendingActions = pendingAction ? [pendingAction] : [];
  const msg = createMessage("assistant", reply, pendingActions);
  session.messages.push(msg);
  return msg;
}

function updateApprovalState(session, messageIndex, actionId, newStatus, result = null) {
  const msg = session.messages[messageIndex];
  if (!msg) return;
  const state = msg.approvalStates.find(s => s.actionId === actionId);
  if (state) {
    state.status = newStatus;
    state.result = result;
  }
}
```

## 6. React Hook 封装

- [x] 6.1 实现 useSessionManager 自定义 Hook

```jsx
import { useState, useEffect, useCallback } from 'react';

export function useSessionManager() {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    const loaded = loadSessions();
    setSessions(loaded);
    setActiveId(loaded[0]?.id || "");
  }, []);

  const activeSession = sessions.find(s => s.id === activeId) || sessions[0];

  const handleNewSession = useCallback(() => {
    return newSession(sessions, setSessions, setActiveId);
  }, [sessions]);

  const handleSwitchSession = useCallback((id) => {
    switchSession(id, setActiveId);
  }, []);

  const handleDeleteSession = useCallback((id) => {
    deleteSession(id, sessions, setSessions, activeId, setActiveId);
  }, [sessions, activeId]);

  const updateSessions = useCallback((updater) => {
    setSessions(prev => {
      const updated = updater(prev);
      saveSessions(updated);
      return updated;
    });
  }, []);

  return {
    sessions,
    activeSession,
    activeId,
    handleNewSession,
    handleSwitchSession,
    handleDeleteSession,
    updateSessions
  };
}
```
