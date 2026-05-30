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
- **THEN** agent executes the tool, sends result back to LLM, and returns the generated reply

#### Scenario: Multiple sequential tool calls
- **WHEN** user sends "查一下订单123、124、125状态" and LLM returns multiple tool_calls
- **THEN** agent executes all tool calls, collects results, sends them back to LLM, and returns the consolidated reply

### Requirement: Risk-level-routing for tool calls
The system SHALL check each tool call's risk level (SAFE/CAUTION/DANGER) before execution and route accordingly: SAFE executes directly, CAUTION checks limits then executes, DANGER creates pending action for approval.

#### Scenario: SAFE tool executes directly
- **WHEN** LLM returns tool_call for query_order (SAFE)
- **THEN** agent executes the tool immediately without approval

#### Scenario: CAUTION tool checks limits
- **WHEN** LLM returns tool_call for create_order with qty=3 (within limit)
- **THEN** agent executes the tool after limit check passes

#### Scenario: CAUTION tool exceeds limits
- **WHEN** LLM returns tool_call for create_order with qty=10 (exceeds max_items=5)
- **THEN** agent returns TOOL_LIMIT error without executing

#### Scenario: DANGER tool creates pending action
- **WHEN** LLM returns tool_call for update_order
- **THEN** agent creates a pending action and returns it to the frontend for approval

### Requirement: System prompt with tool descriptions
The system SHALL construct a system prompt that defines the agent as an ERP assistant and lists all available tools with their descriptions and parameter schemas.

#### Scenario: System prompt includes tool context
- **WHEN** agent constructs messages for LLM
- **THEN** system prompt includes role definition and all tool schemas are passed via the tools parameter
