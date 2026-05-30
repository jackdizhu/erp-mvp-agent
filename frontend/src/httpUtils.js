const API_BASE = "http://localhost:8000";

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

  const res = await chatStream(sessionId, message, history);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
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