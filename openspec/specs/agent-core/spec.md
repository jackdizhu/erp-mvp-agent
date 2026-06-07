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
