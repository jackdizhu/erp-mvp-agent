## Purpose

Delta spec: agent core no longer imports `TOOL_SCHEMAS` or `execute_tool` directly from `app/tools.py`. Instead it accesses tools through `app/erp_client.py`, and imports `ApprovalManager` from `app/approval_core.py` instead of `app/approval.py`.

## MODIFIED Requirements

### Requirement: Agent loop with native Tool Calling
The system SHALL obtain tool schemas via `erp_client.get_tools()` instead of importing `TOOL_SCHEMAS` from `app/tools.py`. Tool execution SHALL be performed via `erp_client.execute_tool(name, args)` instead of direct `execute_tool()` call.

#### Scenario: Direct reply without tool
- **WHEN** user sends "你好" and LLM returns finish_reason=stop
- **THEN** agent returns the LLM's content directly as reply (unchanged)

#### Scenario: Single tool call and reply
- **WHEN** user sends "查询订单123" and LLM returns tool_calls for query_order
- **THEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "123"})`, gets result, sends to LLM, returns reply

### Requirement: Risk-level-routing for tool calls
The system SHALL check each tool call's risk level using `TOOL_RISK_LEVELS` from `erp_app/config.py` (accessed via `erp_client`) instead of `app/config.py`.

#### Scenario: SAFE tool executes directly
- **WHEN** LLM returns tool_call for query_order (SAFE)
- **THEN** agent executes via `erp_client.execute_tool()` immediately without approval

#### Scenario: DANGER tool creates pending action
- **WHEN** LLM returns tool_call for update_order
- **THEN** agent creates a pending action via `approval_core.create_pending()` and retrieves detail via `erp_client.get_approval_detail()`, returns to frontend for approval
