## Purpose

Define the new log event types recorded by `SessionLogger` for the Skill execution path: `skill_matched`, `workflow_step`, `workflow_result`, `skill_failed`. These extend the existing jsonl audit log with Skill-specific events, enabling full reconstruction of Skill-triggered tool call chains post-hoc.

## ADDED Requirements

### Requirement: log_skill_matched method
The system SHALL provide `SessionLogger.log_skill_matched(skill_name, category, has_workflow, has_handler, correlation_id, prompt_fragment)` that writes a `skill_matched` event to the jsonl log.

#### Scenario: Standard log entry
- **WHEN** log_skill_matched is called with skill_name="query-order-edit-address", category="preset", has_workflow=true, has_handler=true, correlation_id="skill_exec_abc123"
- **THEN** log writes: `{"timestamp": "...", "type": "skill_matched", "session_id": "...", "data": {"skill_name": "query-order-edit-address", "category": "preset", "has_workflow": true, "has_handler": true, "correlation_id": "skill_exec_abc123", "prompt_fragment": "修改收货地址流程：..."}}`

#### Scenario: prompt_fragment not truncated
- **WHEN** prompt_fragment is 600 characters long
- **THEN** log entry contains the full 600 characters (not truncated, per design D7)

#### Scenario: Empty prompt_fragment
- **WHEN** log_skill_matched is called with prompt_fragment=""
- **THEN** log entry contains `"prompt_fragment": ""` (empty string, not omitted)

### Requirement: log_workflow_step method
The system SHALL provide `SessionLogger.log_workflow_step(correlation_id, skill_name, step_id, type, status, tool?, instruction?, result?, error?)` that writes a `workflow_step` event.

#### Scenario: tool_call step success
- **WHEN** log_workflow_step is called with step_id="batch_query", type="tool_call", tool="query_order", status="completed", result={"success": true, "data": {...}}
- **THEN** log writes: `{"type": "workflow_step", "data": {"correlation_id": "...", "skill_name": "...", "step_id": "batch_query", "type": "tool_call", "tool": "query_order", "status": "completed", "result": {...}}}`

#### Scenario: prompt step logged
- **WHEN** log_workflow_step is called with type="prompt", instruction="从用户消息提取订单号"
- **THEN** log entry has `type: "prompt"`, `instruction: "..."` (no tool / result fields)

#### Scenario: Step failure
- **WHEN** log_workflow_step is called with status="failed", error="HTTP 500"
- **THEN** log entry has `error: "HTTP 500"` and `result: null` (or omitted)

#### Scenario: instruction truncated
- **WHEN** instruction is longer than 200 characters (per design D7)
- **THEN** log entry contains the first 200 characters followed by "..." (e.g., `"instruction": "从用户消息中提取所有订单号，返回 JSON 数组结构化数据，便于后续批..."`)

### Requirement: log_workflow_result method
The system SHALL provide `SessionLogger.log_workflow_result(correlation_id, skill_name, success, need_approval, need_more_info, step_count)` that writes a `workflow_result` event.

#### Scenario: Handler success with approval
- **WHEN** log_workflow_result is called with success=true, need_approval=true, need_more_info=false, step_count=2
- **THEN** log entry: `{"type": "workflow_result", "data": {"correlation_id": "...", "skill_name": "...", "success": true, "need_approval": true, "need_more_info": false, "step_count": 2}}`

#### Scenario: YAML success with need_more_info
- **WHEN** log_workflow_result is called with need_more_info=true
- **THEN** log entry has `need_more_info: true, need_approval: false`

### Requirement: log_skill_failed method
The system SHALL provide `SessionLogger.log_skill_failed(correlation_id, skill_name, error_code, error_detail, failed_step_id?)` that writes a `skill_failed` event.

#### Scenario: Handler exception
- **WHEN** log_skill_failed is called with error_code="SKILL_EXECUTION_FAILED", error_detail="无法识别订单号", failed_step_id=null
- **THEN** log entry: `{"type": "skill_failed", "data": {"correlation_id": "...", "skill_name": "...", "error_code": "SKILL_EXECUTION_FAILED", "error_detail": "无法识别订单号"}}`

#### Scenario: YAML step failure
- **WHEN** log_workflow_step status="failed" with step_id="batch_query" propagates to log_skill_failed
- **THEN** log_skill_failed entry includes `failed_step_id: "batch_query"`

#### Scenario: error_detail truncated
- **WHEN** error_detail is longer than 200 characters
- **THEN** log entry contains first 200 chars + "..."

### Requirement: Log write resilience
The log methods SHALL be wrapped in try/except so that a log write failure does not break the agent's main flow.

#### Scenario: Disk full
- **WHEN** log file write raises OSError
- **THEN** exception is silently caught (per existing `_write` behavior at agent_logger.py:67), agent continues normally

#### Scenario: Permission denied
- **WHEN** log directory is not writable
- **THEN** log entry is dropped; no exception propagates to caller

### Requirement: Backward compatibility
The new log methods SHALL coexist with existing methods (`log_tool_call`, `log_tool_result`, etc.); no existing method's signature or behavior changes.

#### Scenario: Non-Skill chat
- **WHEN** user sends a non-Skill message
- **THEN** log records `llm_request`, `llm_response`, `tool_call`, `tool_result` as before; no skill_* events

#### Scenario: Existing tests
- **WHEN** existing test fixtures assert on log entry structure for tool_call
- **THEN** test continues to pass (no fields added/removed from existing entries)
