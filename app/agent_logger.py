import json
import traceback
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any


class SessionLogger:
    MAX_FILES = 30
    MAX_DAYS = 7
    STREAM_BUFFER_SIZE = 30  # 累积 30 字符后写入
    STREAM_FLUSH_INTERVAL = 0.1  # 100ms 超时写入

    def __init__(self, session_id: str, log_dir: str = "logs"):
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self._start_time = datetime.now()
        self._ensure_clean()
        # 流式日志缓冲区
        self._stream_buffer = ""
        self._stream_last_write = datetime.now()
        self._stream_timer = None
        self._stream_lock = threading.Lock()

    def _ensure_clean(self):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(
            self.log_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime
        )
        if len(files) > self.MAX_FILES:
            for f in files[:-self.MAX_FILES]:
                f.unlink()
        cutoff = datetime.now() - timedelta(days=self.MAX_DAYS)
        for f in files:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()

    def _sanitize_messages(self, messages: list) -> list:
        if not messages:
            return messages
        result = []
        for msg in messages:
            sanitized = dict(msg)
            if isinstance(sanitized.get("content"), str):
                sanitized["content"] = sanitized["content"].replace(
                    "api_key", "***REDACTED***_api_key"
                )
            result.append(sanitized)
        return result

    def _write(self, event_type: str, data: Any):
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{self._start_time.strftime('%Y-%m-%d')}_{self.session_id}.jsonl"
            filepath = self.log_dir / filename
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "session_id": self.session_id,
                "data": data
            }
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def log_session_start(self, message: str):
        self._write("session_start", {"message": message})

    def log_llm_request(self, messages: list, tools: Optional[list] = None):
        data = {
            "messages": self._sanitize_messages(messages),
        }
        if tools:
            data["tools_count"] = len(tools)
        self._write("llm_request", data)

    def log_llm_response(self, finish_reason: str, content: Optional[str], tool_calls: Optional[list]):
        data = {
            "finish_reason": finish_reason,
            "content_length": len(content) if content else 0,
            "tool_calls_count": len(tool_calls) if tool_calls else 0,
        }
        self._write("llm_response", data)

    def log_tool_call(self, tool: str, args: dict, risk_level: str):
        self._write("tool_call", {
            "tool": tool,
            "args": args,
            "risk": risk_level
        })

    def log_tool_result(self, tool: str, result: Optional[dict] = None, error: Optional[dict] = None):
        data = {"tool": tool}
        if result:
            data["result"] = result
        if error:
            data["error"] = error
        self._write("tool_result", data)

    def log_approval_pending(self, action_id: str, summary: str):
        self._write("approval_pending", {
            "action_id": action_id,
            "summary": summary
        })

    def log_approval_result(self, action_id: str, approved: bool):
        self._write("approval_result", {
            "action_id": action_id,
            "approved": approved
        })

    # ---------- Skill observability events (decision D7) ----------

    @staticmethod
    def _truncate(text: str, max_len: int = 200) -> str:
        """Truncate text to max_len chars + '...' if longer. Used for non-prompt_fragment fields."""
        if text is None:
            return ""
        return text[:max_len] + "..." if len(text) > max_len else text

    def log_skill_matched(
        self,
        skill_name: str,
        category: str,
        has_workflow: bool,
        has_handler: bool,
        correlation_id: str,
        prompt_fragment: str,
    ) -> None:
        """Record skill match event. prompt_fragment is NOT truncated (decision D7)."""
        self._write("skill_matched", {
            "skill_name": skill_name,
            "category": category,
            "has_workflow": has_workflow,
            "has_handler": has_handler,
            "correlation_id": correlation_id,
            "prompt_fragment": prompt_fragment or "",
        })

    def log_workflow_step(
        self,
        correlation_id: str,
        skill_name: str,
        step_id: str,
        type: str,
        status: str,
        tool: Optional[str] = None,
        instruction: Optional[str] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record per-step execution. instruction is truncated to 200 chars."""
        data: dict = {
            "correlation_id": correlation_id,
            "skill_name": skill_name,
            "step_id": step_id,
            "type": type,
            "status": status,
        }
        if tool is not None:
            data["tool"] = tool
        if instruction is not None:
            data["instruction"] = self._truncate(instruction, 200)
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error
        self._write("workflow_step", data)

    def log_workflow_result(
        self,
        correlation_id: str,
        skill_name: str,
        success: bool,
        need_approval: bool,
        need_more_info: bool,
        step_count: int,
    ) -> None:
        """Record Skill execution final result."""
        self._write("workflow_result", {
            "correlation_id": correlation_id,
            "skill_name": skill_name,
            "success": success,
            "need_approval": need_approval,
            "need_more_info": need_more_info,
            "step_count": step_count,
        })

    def log_skill_failed(
        self,
        correlation_id: str,
        skill_name: str,
        error_code: str,
        error_detail: str,
        failed_step_id: Optional[str] = None,
    ) -> None:
        """Record Skill execution failure. error_detail truncated to 200 chars."""
        data: dict = {
            "correlation_id": correlation_id,
            "skill_name": skill_name,
            "error_code": error_code,
            "error_detail": self._truncate(error_detail, 200),
        }
        if failed_step_id is not None:
            data["failed_step_id"] = failed_step_id
        self._write("skill_failed", data)

    def log_skill_fragment_applied(
        self,
        fragment_preview: str,
        fragment_length: int,
    ) -> None:
        """Record that Skill fragments were injected into the system prompt (audit trail)."""
        self._write("skill_fragment_applied", {
            "fragment_preview": self._truncate(fragment_preview, 200),
            "fragment_length": fragment_length,
        })

    def log_error(self, error_type: str, message: str):
        self._write("error", {
            "error_type": error_type,
            "message": message,
            "stack": traceback.format_exc()
        })

    def log_session_end(self, duration_ms: int):
        self._write("session_end", {
            "duration_ms": duration_ms
        })

    def log_stream_chunk(self, content: str):
        """流式日志：使用缓冲区批量写入，减少日志碎片化"""
        with self._stream_lock:
            self._stream_buffer += content
            now = datetime.now()

            # 取消待执行的定时器
            if self._stream_timer:
                self._stream_timer.cancel()
                self._stream_timer = None

            # 缓冲区达到阈值，立即写入
            if len(self._stream_buffer) >= self.STREAM_BUFFER_SIZE:
                self._flush_stream_buffer()
            else:
                # 设置定时器，超时后写入
                elapsed = (now - self._stream_last_write).total_seconds()
                if elapsed >= self.STREAM_FLUSH_INTERVAL:
                    self._flush_stream_buffer()
                else:
                    # 延迟写入
                    delay = self.STREAM_FLUSH_INTERVAL - elapsed
                    self._stream_timer = threading.Timer(delay, self._delayed_flush)
                    self._stream_timer.daemon = True
                    self._stream_timer.start()

    def _flush_stream_buffer(self):
        """立即刷新缓冲区"""
        if self._stream_buffer:
            self._write("stream_chunk", {
                "content": self._stream_buffer,
                "length": len(self._stream_buffer)
            })
            self._stream_buffer = ""
            self._stream_last_write = datetime.now()

    def _delayed_flush(self):
        """定时器回调：延迟刷新"""
        with self._stream_lock:
            self._flush_stream_buffer()