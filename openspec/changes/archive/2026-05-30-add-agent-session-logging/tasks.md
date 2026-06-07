# Tasks: Agent Session Logging

## 1. Logger Module Implementation

- [x] 1.1 Create `app/agent_logger.py` with SessionLogger class
- [x] 1.2 Implement `_sanitize_messages()` to redact api_key
- [x] 1.3 Implement `_write()` method for JSONL append
- [x] 1.4 Implement `_ensure_clean()` cleanup logic (30 sessions / 7 days)
- [x] 1.5 Implement `log_session_start()` event method
- [x] 1.6 Implement `log_llm_request()` event method
- [x] 1.7 Implement `log_llm_response()` event method
- [x] 1.8 Implement `log_tool_call()` event method
- [x] 1.9 Implement `log_tool_result()` event method
- [x] 1.10 Implement `log_approval_pending()` event method
- [x] 1.11 Implement `log_approval_result()` event method
- [x] 1.12 Implement `log_error()` event method
- [x] 1.13 Implement `log_session_end()` event method
- [x] 1.14 Implement `log_stream_chunk()` event method for streaming

## 2. Agent Integration

- [x] 2.1 Add logger initialization in `chat()` function
- [x] 2.2 Add `session_start` log in `chat()`
- [x] 2.3 Add `llm_request` / `llm_response` logs around `call_llm()`
- [x] 2.4 Add `tool_call` / `tool_result` logs in `_execute_safe()`
- [x] 2.5 Add `approval_pending` / `approval_result` logs in approval flow
- [x] 2.6 Add `error` log in exception handlers
- [x] 2.7 Add `session_end` log before return
- [x] 2.8 Mirror logging for `stream_chat()` function
- [x] 2.9 Add `stream_chunk` logging in streaming callback

## 3. Testing & Verification

- [x] 3.1 Verify log directory is created if not exists
- [x] 3.2 Test session log file naming: `{date}_{session_id}.jsonl`
- [x] 3.3 Verify JSONL format (one JSON object per line)
- [x] 3.4 Test cleanup: verify files > 30 are removed
- [x] 3.5 Test cleanup: verify files > 7 days are removed
- [x] 3.6 Verify api_key is redacted in logs
- [x] 3.7 Test streaming logs capture all chunks

## 4. Documentation

- [x] 4.1 Update `logs/README.md` with usage instructions
- [x] 4.2 Document log file structure and event types