## Purpose

Define the workflow step progress tracking: real-time update of step status (pending → completed / failed / pending_approval) as `workflow_step` SSE events arrive, plus cumulative step count display.

## ADDED Requirements

### Requirement: Real-time step progress update
The system SHALL append incoming `workflow_step` events to the message's `workflowSteps` array in arrival order, with each step showing its current status.

#### Scenario: Step appended on event
- **WHEN** SSE event `workflow_step` arrives with `{step_id: "parse_input", type: "prompt", status: "completed"}`
- **THEN** `message.workflowSteps` is updated to `[{step_id: "parse_input", type: "prompt", status: "completed"}]`

#### Scenario: Multiple steps accumulate
- **WHEN** 3 `workflow_step` events arrive sequentially for the same correlation_id
- **THEN** `message.workflowSteps` ends as a 3-element array preserving arrival order

#### Scenario: Step status updated in place
- **WHEN** a step's status changes (e.g., from "pending" to "completed")
- **THEN** the corresponding entry in `workflowSteps` is updated in place (matched by step_id), not appended as a new entry

### Requirement: Step progress count display
The system SHALL display cumulative step progress in the SkillCard header as "X/Y 步已完成" where X is completed count and Y is total.

#### Scenario: Partial completion
- **WHEN** 3 steps total and 2 completed
- **THEN** header shows "2/3 步已完成"

#### Scenario: All complete
- **WHEN** all steps have status "completed"
- **THEN** header shows "3/3 步已完成" + green checkmark

#### Scenario: Step failure
- **WHEN** 3 steps total, 1 completed, 1 failed
- **THEN** header shows "1/3 步已完成 (1 失败)" + red warning icon

#### Scenario: Pending approval
- **WHEN** a step has status "pending_approval"
- **THEN** header counts it as "paused" (not completed): "1/3 步已完成 (1 待审批)"

### Requirement: Step type indicator
The system SHALL visually distinguish tool_call steps (with tool name) from prompt steps (with instruction icon).

#### Scenario: tool_call step display
- **WHEN** step has type="tool_call", tool="query_order"
- **THEN** row shows: `🔧 query_order` (gear icon + monospace tool name)

#### Scenario: prompt step display
- **WHEN** step has type="prompt", instruction="从用户消息提取订单号"
- **THEN** row shows: `💬 prompt` + first 50 chars of instruction (truncated with `...` if longer)

#### Scenario: Tool invocation result preview
- **WHEN** step has result_summary="订单 123 状态: shipping"
- **THEN** row shows small muted text: `→ 订单 123 状态: shipping` (truncated to 80 chars)

### Requirement: Step timing display
The system SHALL record and display the elapsed time for each completed step (in milliseconds).

#### Scenario: Fast step
- **WHEN** step completed in 150ms
- **THEN** row shows timing badge `150ms` (gray, small monospace)

#### Scenario: Slow step
- **WHEN** step completed in 2500ms
- **THEN** row shows timing badge `2.5s` (gray if < 5s, orange if 5-10s, red if > 10s)

#### Scenario: Timing in SSE event
- **WHEN** agent emits workflow_step with `elapsed_ms: 150`
- **THEN** frontend reads elapsed_ms directly; no client-side timing calculation
