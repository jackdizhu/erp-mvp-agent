# Agent Session Logging

## Overview

The agent session logging system records structured event logs for each chat session, enabling debugging, problem diagnosis, and call flow analysis.

## Log Directory

```
logs/
├── 2026-05-30_abc12345.jsonl
├── 2026-05-30_xyz98765.jsonl
└── 2026-05-29_def45678.jsonl
```

## Log File Naming

Format: `{date}_{session_id}.jsonl`

Example: `2026-05-30_abc12345.jsonl`

- `date`: Session start date (YYYY-MM-DD)
- `session_id`: Unique session identifier (8 characters)
- `.jsonl`: JSON Lines format (one JSON object per line)

## Event Types

| Event Type | Description |
|------------|-------------|
| `session_start` | Session begins with user message |
| `llm_request` | LLM API request with sanitized messages |
| `llm_response` | LLM API response (finish_reason, content, tool_calls) |
| `tool_call` | Tool execution with name, args, risk level |
| `tool_result` | Tool execution result or error |
| `approval_pending` | DANGER action awaiting user approval |
| `approval_result` | Approval decision (approved/rejected) |
| `stream_chunk` | Streaming response chunk |
| `error` | Error with type, message, and stack trace |
| `session_end` | Session completion with duration |

## Log Entry Structure

```json
{
  "timestamp": "2026-05-30T15:30:00.123456",
  "type": "llm_request",
  "session_id": "abc12345",
  "data": {
    "messages": [...],
    "tools_count": 5
  }
}
```

## Cleanup Policy

- **Maximum files**: 30 most recent sessions
- **Maximum age**: 7 days
- **Trigger**: Automatic on each new session

## Security

- `api_key` values are automatically redacted to `***REDACTED***_api_key`
- Only standard library modules used (no external dependencies)

## Usage

Logs are automatically generated when:

1. API request includes `session_id` field
2. The session ID must be provided by the client

### API Request Example

```json
POST /chat
{
  "message": "查询订单123的状态",
  "session_id": "abc12345"
}
```

## Analysis Commands

```bash
# View all events for a session
cat logs/2026-05-30_abc12345.jsonl

# Filter by event type
grep '"type":"tool_call"' logs/2026-05-30_abc12345.jsonl

# Pretty print with jq
cat logs/2026-05-30_abc12345.jsonl | jq

# Count events by type
cat logs/2026-05-30_abc12345.jsonl | jq -r '.type' | sort | uniq -c
```