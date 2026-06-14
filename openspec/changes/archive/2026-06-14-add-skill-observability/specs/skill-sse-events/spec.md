## Purpose

Define the new SSE event types emitted by the agent on the Skill execution path: `skill_matched`, `workflow_step`, `workflow_result`, `skill_failed`. These are additive to the existing `tool_call` / `tool_result` / `reply_chunk` / `done` events and provide full observability of Skill behavior to the frontend.

## ADDED Requirements

### Requirement: skill_matched event emission
The system SHALL emit a `skill_matched` SSE event when the Skill registry matches a user message to a Skill, before the executor runs.

#### Scenario: Match event payload
- **WHEN** user sends "查一下订单 ORD-001 状态" and query-order-search skill is matched
- **THEN** agent emits `event: skill_matched\ndata: {"name": "query-order-search", "category": "preset", "description": "...", "tools": ["query_order"], "has_workflow": false, "has_handler": false, "correlation_id": "skill_exec_a1b2c3d4e5f6"}\n\n`

#### Scenario: No event when no skill matches
- **WHEN** user sends "今天天气怎么样" and no skill matches
- **THEN** agent does NOT emit any skill_matched event (existing tool_call path used)

#### Scenario: Event before executor call
- **WHEN** a skill is matched
- **THEN** skill_matched event is emitted BEFORE `SkillExecutor.execute()` is called (frontend can render SkillCard immediately)

### Requirement: workflow_step event emission
The system SHALL emit a `workflow_step` SSE event when each YAML workflow step (tool_call or prompt) completes, with status `completed` / `failed` / `pending_approval`.

#### Scenario: tool_call step completed
- **WHEN** a YAML workflow's `tool_call` step finishes successfully
- **THEN** agent emits `event: workflow_step\ndata: {"correlation_id": "skill_exec_...", "step_id": "batch_query", "type": "tool_call", "tool": "query_order", "status": "completed", "result_summary": "..."}\n\n`

#### Scenario: prompt step recorded
- **WHEN** a YAML workflow's `prompt` step is recorded (no tool call)
- **THEN** agent emits workflow_step event with `type: "prompt"`, `instruction: "..."`, `status: "completed"`

#### Scenario: step failure
- **WHEN** a tool_call step raises an exception
- **THEN** agent emits workflow_step with `status: "failed"`, `error: "..."` BEFORE the skill_failed event

### Requirement: workflow_result event emission
The system SHALL emit a `workflow_result` SSE event when YAML or Python handler execution completes successfully (with or without need_approval / need_more_info flags).

#### Scenario: Handler success with need_approval
- **WHEN** Python handler returns `WorkflowResult(need_approval=True, intermediate_data={...})`
- **THEN** agent emits `event: workflow_result\ndata: {"correlation_id": "skill_exec_...", "success": true, "need_approval": true, "need_more_info": false, "step_count": 3}\n\n`

#### Scenario: YAML success with need_more_info
- **WHEN** YAML workflow's prompt step needs more user input
- **THEN** agent emits workflow_result with `need_more_info: true`

#### Scenario: No event on failure
- **WHEN** executor returns success=False
- **THEN** agent emits `skill_failed` instead of `workflow_result`

### Requirement: skill_failed event emission
The system SHALL emit a `skill_failed` SSE event when executor returns success=False or raises an unhandled exception.

#### Scenario: Handler exception
- **WHEN** Python handler raises an exception during execution
- **THEN** agent emits `event: skill_failed\ndata: {"correlation_id": "skill_exec_...", "name": "my-skill", "error_code": "SKILL_EXECUTION_FAILED", "error_detail": "..."}\n\n`

#### Scenario: YAML step failure
- **WHEN** YAML workflow's tool_call step fails
- **THEN** agent emits skill_failed with `failed_step_id: "batch_query"` and error message

#### Scenario: Missing approval contract
- **WHEN** handler returns need_approval but intermediate_data is missing required keys
- **THEN** agent emits skill_failed with `error_detail: "missing approval contract"`

### Requirement: SSE event format conformance
All new skill_* events SHALL follow the existing SSE format `event: <name>\ndata: <json>\n\n` with UTF-8 encoded JSON `data` payload.

#### Scenario: UTF-8 Chinese content
- **WHEN** skill name contains Chinese (e.g., "查询订单")
- **THEN** JSON payload is `ensure_ascii=False` encoded (Chinese visible in stream)

#### Scenario: Event ordering
- **WHEN** a skill is executed
- **THEN** events arrive in order: `skill_matched` → `workflow_step` (×N) → `workflow_result` (or `skill_failed`)

### Requirement: Backward compatibility
The new skill_* events SHALL be additive; existing tool_call / tool_result / reply_chunk / done events SHALL remain unchanged and continue to be emitted for non-Skill chat paths.

#### Scenario: Non-Skill path unchanged
- **WHEN** user sends a message that does not match any skill (e.g., "今天天气怎么样")
- **THEN** no skill_* events are emitted; tool_call / tool_result events fire as before

#### Scenario: Frontend ignores unknown events
- **WHEN** frontend receives an event type it doesn't handle
- **THEN** frontend safely ignores it without error (e.g., during phased rollout)
