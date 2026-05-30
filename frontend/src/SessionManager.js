import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = "erp_agent_sessions";

export function createSession() {
  return {
    id: `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title: "新会话",
    createdAt: new Date().toISOString(),
    messages: []
  };
}

export function createMessage(role, content, pendingActions = null) {
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

export function saveSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error("Failed to save sessions:", e);
  }
}

export function loadSessions() {
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

export function newSession(sessions, setSessions, setActiveId) {
  const session = createSession();
  const updated = [session, ...sessions];
  setSessions(updated);
  setActiveId(session.id);
  saveSessions(updated);
  return session;
}

export function switchSession(id, setActiveId) {
  setActiveId(id);
}

export function deleteSession(id, sessions, setSessions, activeId, setActiveId) {
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

export function autoTitle(session, message) {
  if (session.messages.length === 0 || session.title !== "新会话") {
    return session.title;
  }
  return message.length > 20 ? message.slice(0, 20) + "..." : message;
}

export function truncateHistory(messages, n = 6) {
  if (messages.length <= n) {
    return messages.map(m => ({ role: m.role, content: m.content }));
  }
  return messages
    .slice(-n)
    .map(m => ({ role: m.role, content: m.content }));
}

export function addAssistantMessage(session, reply, toolCalls, pendingAction) {
  const pendingActions = pendingAction ? [pendingAction] : [];
  const msg = createMessage("assistant", reply, pendingActions);
  session.messages.push(msg);
  return msg;
}

export function updateApprovalState(session, messageIndex, actionId, newStatus, result = null) {
  const msg = session.messages[messageIndex];
  if (!msg) return;
  const state = msg.approvalStates.find(s => s.actionId === actionId);
  if (state) {
    state.status = newStatus;
    state.result = result;
  }
}

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
      const updated = updater([...prev.map(s => ({...s, messages: [...s.messages]}))]);
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
    updateSessions,
    createMessage,
    addAssistantMessage,
    updateApprovalState,
    autoTitle,
    truncateHistory
  };
}
