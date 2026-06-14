## Purpose

Define the failure semantics for Skill execution: (1) when a Skill is matched but execution fails, the agent does NOT fall back to `detect_tool_intent` and returns a `SKILL_EXECUTION_FAILED` error; (2) when a Skill needs more information, the agent injects `intermediate_data` into the system prompt and asks the LLM to continue the conversation.

## Requirements

### Requirement: Skill execution failure returns dedicated error
The system SHALL define a new error code `SKILL_EXECUTION_FAILED` (source="skill", recoverable=true) in `app/errors.py`, returned when a matched skill's executor returns `WorkflowResult.success=False`.

#### Scenario: Handler raises exception
- **WHEN** SkillHandler.execute() raises an exception
- **THEN** executor catches it and returns WorkflowResult(success=False, error=str(e))
- **AND** agent returns build_error_response(skill_execution_failed(skill_name, error))

#### Scenario: YAML workflow step fails
- **WHEN** a tool_call step in YAML workflow raises exception
- **THEN** executor returns WorkflowResult(success=False, error="步骤 'X' 执行失败: ...")
- **AND** agent returns build_error_response(skill_execution_failed(skill_name, error))

### Requirement: No fallback to detect_tool_intent on Skill failure
The system SHALL NOT call `intent_detector.detect_tool_intent()` or `_force_tool_retry()` when a matched skill's execution fails; the SKILL_EXECUTION_FAILED error is the terminal response.

#### Scenario: Failure without fallback
- **WHEN** user message matched query-order-edit-address and handler failed
- **THEN** response is SKILL_EXECUTION_FAILED, NOT a retried update_order tool call

#### Scenario: Failure without tool retry
- **WHEN** user message matched query-order-edit-address and YAML workflow step failed
- **THEN** system does NOT call call_llm with retry prompt, does NOT create pending action for update_order

### Requirement: need_more_info injects intermediate_data into system prompt
The system SHALL handle `WorkflowResult.need_more_info=True` by: (1) building a new system message that describes the skill state with intermediate_data, (2) calling call_llm WITHOUT tools parameter, (3) returning the LLM's reply as the user-facing response.

#### Scenario: Order address missing
- **WHEN** user says "修改订单 ORD-001 的收货地址" and handler finds order but no new address
- **THEN** handler returns need_more_info=True, intermediate_data={order_id, current_address}
- **AND** agent appends system message: "Skill 'query-order-edit-address' 已查询订单 ORD-001，当前地址: 上海市xxx。请基于以上信息继续与用户对话以获取新地址。"
- **AND** agent calls call_llm(messages, tools=None) and returns the LLM's reply

#### Scenario: LLM continues conversation
- **WHEN** intermediate_data injected and LLM generates reply
- **THEN** reply is a user-facing follow-up question (e.g., "当前地址是上海xxx，请告诉我要改成什么？")
- **AND** response has no tool_calls and no pending_action

### Requirement: Size limit on intermediate_data injection
The system SHALL truncate `intermediate_data` JSON serialization to 2000 characters when injecting into system prompt; longer content is replaced with "数据过长，已省略".

#### Scenario: Small intermediate_data
- **WHEN** intermediate_data is {order_id: "ORD-001", current_address: "上海xxx"} (< 2000 chars)
- **THEN** full content is injected

#### Scenario: Large intermediate_data
- **WHEN** intermediate_data JSON serialization is 5000 chars
- **THEN** system message uses "数据过长，已省略" placeholder

### Requirement: Subsequent user message re-enters Skill matching
The system SHALL re-run `SkillRegistry.match_skill()` on the user's next message; the prior `need_more_info` state does NOT persist across chat requests.

#### Scenario: User replies with new address
- **WHEN** user previously triggered need_more_info and now says "改成北京朝阳区"
- **THEN** next /chat call re-matches query-order-edit-address skill and runs full workflow

#### Scenario: No sticky state
- **WHEN** agent does not cache "this session is in skill X" state
- **THEN** each /chat call starts from a clean skill match