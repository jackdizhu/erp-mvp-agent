## Purpose

Define the bridge between Skill workflow execution and the existing approval flow: when a SkillHandler returns `WorkflowResult(need_approval=True)`, the agent layer translates the `intermediate_data` contract into an `approval_core.create_pending()` call. This keeps handlers decoupled from approval infrastructure while reusing the existing two-stage approval UX.

## ADDED Requirements

### Requirement: Handler returns approval contract
The system SHALL require that handlers returning `need_approval=True` populate `intermediate_data` with three keys: `tool` (string, target tool name), `tool_args` (dict, tool call arguments), `approval_summary` (string, human-readable summary for the approval card).

#### Scenario: Valid approval contract
- **WHEN** handler decides to request user approval for an update_order
- **THEN** WorkflowResult(need_approval=True, intermediate_data={"tool": "update_order", "tool_args": {"order_id": "ORD-001", "field": "address", "value": "北京"}, "approval_summary": "修改订单 ORD-001 收货地址为北京"})

#### Scenario: Missing tool key rejected
- **WHEN** intermediate_data lacks "tool" key
- **THEN** agent logs error and returns build_error_response(skill_execution_failed) — does NOT call approval_core

#### Scenario: Missing tool_args rejected
- **WHEN** intermediate_data lacks "tool_args" key
- **THEN** agent returns build_error_response(skill_execution_failed)

### Requirement: Handler does not import approval_core
The system SHALL enforce that handler.py files do not import `app.approval_core` or any approval-layer module; all approval coordination happens in `agent.py`.

#### Scenario: Handler imports approval_core
- **WHEN** handler.py contains `from app.approval_core import ...`
- **THEN** unit test for handler requires approval_core mock — flagged as design violation

#### Scenario: Pure handler contract
- **WHEN** handler.py has only imports of base.py, client_factory, and standard libs
- **THEN** handler can be unit-tested without approval_core present

### Requirement: Agent bridge function
The system SHALL provide `_handle_skill_approval(workflow_result, messages, logger) -> dict` in `app/agent.py` that converts `intermediate_data` to a pending action via `approval_core.create_pending(tool, tool_args, messages)`.

#### Scenario: Successful bridge
- **WHEN** workflow_result has need_approval=True and valid intermediate_data
- **THEN** agent calls approval_core.create_pending(tool, tool_args, messages) and returns chat response with pending_action field

#### Scenario: create_pending returns None
- **WHEN** approval_core.create_pending fails (returns None)
- **THEN** agent returns build_error_response(approval_failed(tool))

#### Scenario: Bridge response format
- **WHEN** bridge succeeds
- **THEN** response contains: reply (with summary prefix), tool_calls list with status="pending_approval", pending_action object

### Requirement: Approval summary format
The system SHALL use `intermediate_data.approval_summary` directly as the prefix of the agent's `reply` field (e.g., "需要确认以下操作：{summary}").

#### Scenario: Summary in reply
- **WHEN** approval_summary = "修改订单 ORD-001 收货地址为北京"
- **THEN** reply field = "需要确认以下操作：修改订单 ORD-001 收货地址为北京"

### Requirement: Reuse existing approval flow
The system SHALL NOT create new approval endpoints or modify approval_store; the skill-driven approval flows through the same `/api/approval/create` and `/api/approval/decide` endpoints as LLM-driven DANGER tool calls.

#### Scenario: Skill approval uses existing endpoints
- **WHEN** skill returns need_approval=True
- **THEN** frontend ApprovalCard consumes the response identically to LLM-driven DANGER approval — no frontend changes needed
