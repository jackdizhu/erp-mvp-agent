# Agent Session Logging

## Purpose

[TBD]

## Requirements

### Requirement: Session-scoped logging with structured events

The logging system SHALL create one JSONL file per session, identified by `{date}_{session_id}.jsonl` pattern, containing timestamped event records for debugging and analysis.

#### Scenario: New session creates log file
- **WHEN** a new chat session starts with session_id "abc123" on 2026-05-30
- **THEN** system creates `logs/2026-05-30_abc123.jsonl`
- **AND** first line is `session_start` event with timestamp

#### Scenario: Session events are appended
- **WHEN** during a session, LLM request, tool call, and tool result occur
- **THEN** each event is appended as a separate JSON line in order
- **AND** file is flushed after each write

### Requirement: Comprehensive event types coverage

The logging system SHALL record all significant events in the agent call chain: LLM interactions, tool executions, approval flows, and errors.

#### Scenario: LLM request is logged
- **WHEN** agent calls `call_llm(messages, tools)`
- **THEN** `llm_request` event is written with sanitized messages (api_key redacted)

#### Scenario: LLM response is logged
- **WHEN** agent receives LLM response
- **THEN** `llm_response` event is written with finish_reason, content, and tool_calls

#### Scenario: Tool execution is logged
- **WHEN** agent executes a tool (SAFE/CAUTION) or queues for approval (DANGER)
- **THEN** `tool_call` event is written with tool name, args, and risk level
- **AND** `tool_result` event is written after execution completes

#### Scenario: Approval flow is logged
- **WHEN** a DANGER-level action requires user approval
- **THEN** `approval_pending` event is written with action_id and summary
- **AND** `approval_result` event is written when user approves/rejects

#### Scenario: Errors are logged with context
- **WHEN** an exception occurs during agent execution
- **THEN** `error` event is written with error type, message, and stack trace

#### Scenario: Session end is logged
- **WHEN** chat session completes (success or failure)
- **THEN** `session_end` event is written with total duration in milliseconds

### Requirement: Automatic log cleanup

The logging system SHALL automatically clean up old log files to prevent unbounded disk usage, keeping the most recent 30 sessions or files within 7 days.

#### Scenario: Cleanup removes excess sessions
- **WHEN** a new session starts and more than 30 log files exist
- **THEN** the oldest files are deleted until only 30 remain

#### Scenario: Cleanup removes expired sessions
- **WHEN** a new session starts
- **THEN** any log files older than 7 days are deleted regardless of count

### Requirement: Log file format compatibility

The logging system SHALL produce JSONL format files compatible with standard Unix tools (grep, jq) for manual analysis.

#### Scenario: Single-line JSON per event
- **WHEN** an event is logged
- **THEN** it is written as a single JSON object on one line
- **AND** the line ends with `\n` (no trailing comma or bracket)

#### Scenario: Common event structure
- **WHEN** any event is logged
- **THEN** the JSON object contains: `timestamp` (ISO 8601), `type` (event name), `session_id`
- **AND** `data` field holds event-specific payload

#### Scenario: Sensitive data sanitization
- **WHEN** LLM messages containing api_key are logged
- **THEN** the api_key value is replaced with `"***REDACTED***"`

### Requirement: Streaming output logging

The logging system SHALL record streaming response chunks when using `stream_chat()` for complete playback capability.

#### Scenario: Stream chunks are logged
- **WHEN** `stream_chat()` receives content chunks from LLM
- **THEN** each chunk is logged as a `stream_chunk` event with partial content

### Requirement: Stream chunk logging with buffering

The system SHALL implement buffered stream chunk logging in SessionLogger to reduce log fragmentation. When log_stream_chunk(content) is called, the content SHALL be accumulated in a buffer. The buffer SHALL be flushed (written to file) when either:
1. The buffer size reaches or exceeds STREAM_BUFFER_SIZE (30 characters), OR
2. The time since last write exceeds STREAM_FLUSH_INTERVAL (100ms)

#### Scenario: Buffer reaches threshold
- **WHEN** log_stream_chunk is called and _stream_buffer length + new content >= 30
- **THEN** _flush_stream_buffer() is called immediately, writing all buffered content as one record

#### Scenario: Buffer timeout
- **WHEN** log_stream_chunk is called and _stream_buffer length + new content < 30
- **THEN** a threading.Timer is scheduled to call _delayed_flush after (STREAM_FLUSH_INTERVAL - elapsed) seconds
- **AND** if a previous timer exists, it is cancelled before scheduling a new one

#### Scenario: Immediate flush on existing timer
- **WHEN** log_stream_chunk is called and a _stream_timer is pending
- **THEN** the pending timer is cancelled before adding content to buffer

### Requirement: Thread-safe logging

The system SHALL use threading.Lock to ensure thread-safe access to _stream_buffer and _stream_timer.

#### Scenario: Concurrent chunk logging
- **WHEN** multiple threads call log_stream_chunk simultaneously
- **THEN** each call acquires _stream_lock before modifying buffer, preventing race conditions

### Requirement: Buffer flush on session end

The system SHALL flush any remaining buffered content when the session ends.

#### Scenario: Pending buffer on session end
- **WHEN** a session ends and _stream_buffer has content
- **THEN** _flush_stream_buffer() is called to write remaining content

### Requirement: Backward compatible logging

The system SHALL maintain the same log entry format (type: "stream_chunk", data: {content, length}) for all flushed records.

#### Scenario: Log content integrity
- **WHEN** multiple chunks "订单" + "查询" + "成功" are logged
- **THEN** the flushed record contains "订单查询成功" with length=6 (not three separate records)

### Requirement: Zero-dependency implementation

The logging system SHALL use only Python standard library modules without external dependencies.

#### Scenario: No external dependencies
- **WHEN** `app/agent_logger.py` is imported
- **THEN** only modules from Python standard library are used (json, pathlib, datetime, os, shutil)