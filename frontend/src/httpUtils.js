const API_PORT = import.meta.env.VITE_API_PORT || "9000";
const API_BASE = `http://localhost:${API_PORT}`;

export async function chatPost(sessionId, message, history) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, history })
  });
  return res.json();
}

export async function chatConfirm(sessionId, actionId, approved, history) {
  const res = await fetch(`${API_BASE}/chat/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action_id: actionId, approved, history })
  });
  return res.json();
}

export async function chatConfirmWithUserOp(sessionId, actionId, approved, history, userOpId) {
  const res = await fetch(`${API_BASE}/chat/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      action_id: actionId,
      approved,
      history,
      user_op_id: userOpId
    })
  });
  return res.json();
}

export async function approvalCreate(actionId, tool, args, sessionId) {
  const res = await fetch(`${API_BASE}/api/approval/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_id: actionId, tool, args, session_id: sessionId })
  });
  return res.json();
}

export async function approvalDecide(actionId, approved, sessionId) {
  const res = await fetch(`${API_BASE}/api/approval/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_id: actionId, approved, session_id: sessionId })
  });
  return res.json();
}

export async function chatStream(sessionId, message, history, signal) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, history }),
    signal
  });
  return res;
}

export async function chatStreamReader(sessionId, message, history, callbacks) {
  const { onThinking, onToolCall, onToolResult, onReplyChunk, onDone, onError } = callbacks;

  let res;
  try {
    res = await chatStream(sessionId, message, history);
  } catch (err) {
    const errorObj = {
      status: 0,
      statusText: "Network Error",
      message: err.message || "Failed to connect to server",
      isNetworkError: true
    };
    onError?.(errorObj);
    return;
  }

  if (!res.ok) {
    let errorBody = "";
    try {
      errorBody = await res.text();
    } catch (_) {
      errorBody = res.statusText;
    }

    const errorObj = {
      status: res.status,
      statusText: res.statusText,
      message: errorBody.slice(0, 200),
      isNetworkError: false
    };
    onError?.(errorObj);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:") && currentEvent) {
        const dataStr = line.slice(5).trim();
        try {
          const data = JSON.parse(dataStr);
          switch (currentEvent) {
            case "thinking": onThinking?.(data); break;
            case "tool_call": onToolCall?.(data); break;
            case "tool_result": onToolResult?.(data); break;
            case "reply_chunk": onReplyChunk?.(data); break;
            case "done": onDone?.(data); break;
          }
        } catch (e) {
          console.warn("Failed to parse SSE data:", dataStr);
        }
      }
    }
  }
}