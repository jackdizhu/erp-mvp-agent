import { useRef, useCallback } from 'react';

const API_BASE = "http://localhost:8000";

export function useStreamingChat() {
  const abortRef = useRef(null);

  const startStream = useCallback(async (message, history, session_id, callbacks) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const { onThinking, onToolCall, onToolResult, onReplyChunk, onDone, onError } = callbacks;

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history, session_id }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

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
                case "thinking":
                  onThinking?.(data);
                  break;
                case "tool_call":
                  onToolCall?.(data);
                  break;
                case "tool_result":
                  onToolResult?.(data);
                  break;
                case "reply_chunk":
                  onReplyChunk?.(data);
                  break;
                case "done":
                  onDone?.(data);
                  break;
                default:
                  break;
              }
            } catch (e) {
              console.warn("Failed to parse SSE data:", dataStr);
            }
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return;
      onError?.(err);
    } finally {
      abortRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  return { startStream, stopStream };
}
