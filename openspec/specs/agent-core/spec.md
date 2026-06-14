## Purpose

Define the core agent loop, risk-level routing, and system prompt behavior for the ERP agent.

## Requirements

### Requirement: Agent loop with native Tool Calling
The system SHALL implement an agent loop that sends messages + tool schemas to LLM via native Tool Calling API, handles both direct replies (finish_reason=stop) and tool calls (finish_reason=tool_calls), and loops until a final reply is generated.

#### Scenario: Direct reply without tool
- **WHEN** user sends "你好" and LLM returns finish_reason=stop
- **THEN** agent returns the LLM's content directly as reply

#### Scenario: Single tool call and reply
- **WHEN** user sends "查询订单123" and LLM returns tool_calls for query_order
- **THEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "123"})`, gets result, sends to LLM, returns reply

#### Scenario: Multiple sequential tool calls
- **WHEN** user sends "查一下订单123、124、125状态" and LLM returns multiple tool_calls
- **THEN** agent executes all tool calls via `erp_client.execute_tool()`, collects results, sends them back to LLM, and returns the consolidated reply

### Requirement: Risk-level-routing for tool calls
The system SHALL check each tool call's risk level using `TOOL_RISK_LEVELS` from `erp_app/config.py` (accessed via `erp_client`) instead of `app/config.py`. SAFE executes directly, CAUTION checks limits then executes, DANGER creates pending action for approval. When confirming a DANGER tool, the system SHALL route by tool mode: MCP tools use `execute_tool_preapproved` with `user_op_id`, ERP tools use `client_factory.execute_tool`.

#### Scenario: SAFE tool executes directly
- **WHEN** LLM returns tool_call for query_order (SAFE)
- **THEN** agent executes via `erp_client.execute_tool()` immediately without approval

#### Scenario: CAUTION tool checks limits
- **WHEN** LLM returns tool_call for create_order with qty=3 (within limit)
- **THEN** agent executes the tool after limit check passes

#### Scenario: CAUTION tool exceeds limits
- **WHEN** LLM returns tool_call for create_order with qty=10 (exceeds max_items=5)
- **THEN** agent returns TOOL_LIMIT error without executing

#### Scenario: DANGER tool creates pending action
- **WHEN** LLM returns tool_call for update_order
- **THEN** agent creates a pending action via `approval_core.create_pending()` and retrieves detail via `erp_client.get_approval_detail()`, returns to frontend for approval

#### Scenario: Confirm MCP DANGER tool with user_op_id
- **WHEN** confirm_action is called with action_id for an MCP tool and user_op_id="uop_xxxxxxxxxxxx"
- **THEN** agent calls mcp_client.execute_tool_preapproved(tool_name, tool_args, user_op_id="uop_xxxxxxxxxxxx") to bypass MCP internal approval

#### Scenario: Confirm ERP DANGER tool
- **WHEN** confirm_action is called with action_id for an ERP tool
- **THEN** agent calls client_factory.execute_tool(tool_name, tool_args) directly

#### Scenario: Confirm MCP tool without preapproved support
- **WHEN** confirm_action is called for MCP tool and mcp_client does not have execute_tool_preapproved method
- **THEN** agent falls back to client_factory.execute_tool(tool_name, tool_args)

### Requirement: System prompt with tool descriptions
The system SHALL obtain tool schemas via `erp_client.get_tools()` instead of importing `TOOL_SCHEMAS` from `app/tools.py`. The system SHALL construct a system prompt that defines the agent as an ERP assistant and lists all available tools with their descriptions and parameter schemas, passing schemas to LLM via the tools parameter.

#### Scenario: System prompt includes tool context
- **WHEN** agent constructs messages for LLM
- **THEN** system prompt includes role definition and all tool schemas are passed via the tools parameter

### Requirement: Skill matching priority
The agent loop SHALL call `SkillRegistry.match_skill(message)` before `intent_detector.detect_tool_intent()`. When a skill is matched, the agent enters the Skill execution path and SHALL NOT call `detect_tool_intent()` or `_force_tool_retry()`. When no skill is matched, the agent falls back to the existing `detect_tool_intent()` flow.

#### Scenario: Skill matched takes priority
- **WHEN** user sends "查一下订单 ORD-001 状态" and the query-order-search skill's intent pattern matches
- **THEN** agent enters Skill path (injects prompt_fragment, runs executor)
- **AND** detect_tool_intent is NOT called

#### Scenario: No skill matched falls back
- **WHEN** user sends a message that matches no skill's intent patterns
- **THEN** agent calls detect_tool_intent and proceeds with the existing tool-call flow

#### Scenario: Skill matched but execution fails
- **WHEN** skill is matched and SkillExecutor returns WorkflowResult(success=False)
- **THEN** agent returns SKILL_EXECUTION_FAILED error
- **AND** does NOT fall back to detect_tool_intent (no forced tool retry)

### Requirement: Skill execution routing
When a skill is matched, the agent SHALL route execution based on the executor result: (1) `success=True` with no flags → return results to user, (2) `need_approval=True` → call `_handle_skill_approval` bridge, (3) `need_more_info=True` → inject `intermediate_data` into system prompt and re-call LLM without tools.

#### Scenario: Skill success returns results
- **WHEN** SkillExecutor returns WorkflowResult(success=True, steps=[...], intermediate_data={...})
- **THEN** agent returns the workflow's intermediate_data as the tool_calls and runs LLM for final reply

#### Scenario: Skill need_approval routes to bridge
- **WHEN** SkillExecutor returns WorkflowResult(need_approval=True, intermediate_data={tool, tool_args, approval_summary})
- **THEN** agent calls `_handle_skill_approval(workflow_result, messages, logger)` which uses approval_core.create_pending

#### Scenario: Skill need_more_info injects context
- **WHEN** SkillExecutor returns WorkflowResult(need_more_info=True, intermediate_data={...})
- **THEN** agent appends system message describing skill state, then calls LLM without tools parameter
- **AND** returns LLM reply as user-facing response

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
