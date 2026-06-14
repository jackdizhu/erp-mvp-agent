## ADDED Requirements

### Requirement: Skill workflow tool execution via client_factory
The system SHALL execute `tool_call` steps in YAML skill workflows by calling `client_factory.execute_tool(tool_name, params)`, reusing the same tool routing layer that powers LLM-driven tool calls. MCP tools SHALL continue to be resolved through `client_factory._mcp_tool_alias` (e.g., `query_order` → `mcp_query_order`).

#### Scenario: MCP tool invoked from skill workflow
- **WHEN** YAML workflow step has tool="query_order" and params={order_id: "ORD-001"}
- **THEN** client_factory.execute_tool resolves "query_order" via _mcp_tool_alias to "mcp_query_order" and routes to the MCP service
- **AND** returns the MCP response as the step result

#### Scenario: ERP local tool invoked from skill workflow
- **WHEN** YAML workflow step has tool="some_local_tool" and only erp_local client is registered
- **THEN** client_factory.execute_tool routes to erp_local adapter (no MCP prefix needed)

#### Scenario: Tool name from skill.yaml uses short name
- **WHEN** skill.yaml declares `tools: [query_order]` (short name) and client_factory has it under "mcp_query_order" (aliased)
- **THEN** validator strips "mcp_" prefix when checking availability and matches successfully

### Requirement: Tool availability check for skill validation
The system SHALL provide `available_tools: List[str]` to `SkillValidator.validate_config` by extracting tool names from `client_factory.get_all_tools()` and stripping the `mcp_` prefix, so skill.yaml's `tools:` field (using short names) can be validated against the active MCP/ERP registration.

#### Scenario: Validator extracts available tools
- **WHEN** `client_factory.get_all_tools()` returns tools with names like `mcp_query_order`, `mcp_update_order`
- **THEN** validator's available_tools list is `["query_order", "update_order", ...]` (prefix stripped)

#### Scenario: Validator reports missing tool
- **WHEN** skill.yaml declares `tools: [nonexistent_tool]` and available_tools is `["query_order", "update_order"]`
- **THEN** validator returns errors=[f"工具 'nonexistent_tool' 未在当前 MCP 注册表中，可选工具: query_order, update_order"]

#### Scenario: Tool declared in skill.yaml matches MCP tool
- **WHEN** skill.yaml declares `tools: [query_order]` and MCP service has registered `mcp_query_order`
- **THEN** validator passes this check (no error)

### Requirement: Risk level routing for skill-driven tool calls
The system SHALL apply the same risk level routing for tool calls originating from skill workflows as for LLM-driven tool calls. When a `tool_call` step references a DANGER-level tool, the step's result SHALL be a `pending_approval` WorkflowStep; the agent layer translates this to the approval flow via `_handle_skill_approval` bridge (see [skill-approval-bridge spec](../skill-approval-bridge/spec.md)).

#### Scenario: SAFE tool from skill workflow
- **WHEN** YAML workflow calls query_order (SAFE)
- **THEN** step result is executed synchronously, WorkflowStep.status="completed", no approval needed

#### Scenario: DANGER tool from skill workflow returns need_approval
- **WHEN** YAML workflow calls update_order (DANGER)
- **THEN** workflow result is need_approval=True with intermediate_data={tool: "update_order", tool_args: {...}, approval_summary: "..."}
- **AND** agent calls _handle_skill_approval to route through approval_core

#### Scenario: DANGER tool detection uses client_factory
- **WHEN** step needs risk level for routing
- **THEN** executor calls `client_factory.get_risk_level(tool_name)` which uses _mcp_tool_alias lookup and returns the tool's risk from the underlying client
