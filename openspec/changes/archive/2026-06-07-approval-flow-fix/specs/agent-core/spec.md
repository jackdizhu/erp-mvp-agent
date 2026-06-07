## MODIFIED Requirements

### Requirement: Risk-level-routing for tool calls
The system SHALL check each tool call's risk level using `TOOL_RISK_LEVELS` from `erp_app/config.py` (accessed via `erp_client`) instead of `app/config.py`. SAFE executes directly, CAUTION checks limits then executes, DANGER creates pending action for approval. When confirming a DANGER tool, the system SHALL route by tool mode: MCP tools use `execute_tool_preapproved` with `user_op_id`, ERP tools use `client_factory.execute_tool`.

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
