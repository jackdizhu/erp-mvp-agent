import { useRef, useCallback } from 'react';
import { chatStreamReader } from './httpUtils';

export function useStreamingChat() {
  const abortRef = useRef(null);

  const startStream = useCallback(async (message, history, session_id, callbacks) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await chatStreamReader(session_id, message, history, callbacks);
    } catch (err) {
      if (err.name === "AbortError") return;
      callbacks.onError?.(err);
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