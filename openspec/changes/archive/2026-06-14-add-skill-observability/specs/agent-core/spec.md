## ADDED Requirements

### Requirement: Skill path SSE event emission
The agent loop SHALL emit `skill_matched` / `workflow_step` / `workflow_result` / `skill_failed` SSE events at defined points in the Skill execution path, in addition to the existing `tool_call` / `tool_result` / `reply_chunk` / `done` events.

#### Scenario: Skill matched event before executor
- **WHEN** a user message matches a Skill and the agent enters the Skill execution path
- **THEN** agent emits `event: skill_matched` with payload `{name, category, description, tools, has_workflow, has_handler, correlation_id}` BEFORE calling `SkillExecutor.execute()`

#### Scenario: Workflow step event per step
- **WHEN** YAML workflow step completes (tool_call or prompt)
- **THEN** agent emits `event: workflow_step` with payload `{correlation_id, step_id, type, tool?, instruction?, status, elapsed_ms?, result_summary?}`

#### Scenario: Workflow result on success
- **WHEN** SkillExecutor returns success=True (any combination of need_approval / need_more_info / normal)
- **THEN** agent emits `event: workflow_result` with payload `{correlation_id, success: true, need_approval, need_more_info, step_count}`

#### Scenario: Skill failed on failure
- **WHEN** SkillExecutor returns success=False or raises an exception
- **THEN** agent emits `event: skill_failed` with payload `{correlation_id, name, error_code: "SKILL_EXECUTION_FAILED", error_detail, failed_step_id?}` (no workflow_result event in this case)

### Requirement: SkillObservability integration
The agent loop SHALL create a `SkillObservability` instance per Skill execution to encapsulate the correlation_id, SSE emission, and log writing.

#### Scenario: Observability instance lifecycle
- **WHEN** a skill is matched
- **THEN** agent creates `obs = SkillObservability(logger=session_logger, on_event=emit_sse)` and passes `obs` to all subsequent emit calls
- **AND** `obs.correlation_id` is a single UUID used for all events/logs of this execution

#### Scenario: Observable in chat() function
- **WHEN** chat() handles a Skill-matched message
- **THEN** the function creates the observability instance inline and uses it across all 4 branch handlers (need_approval, need_more_info, success, failure)

#### Scenario: Observable in stream_chat() function
- **WHEN** stream_chat() handles a Skill-matched message (Phase 3)
- **THEN** same observability pattern applies; `on_event` callback is the existing SSE event emitter
