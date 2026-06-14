## Purpose

Define the tool system including schema definitions, registry, risk levels, quantity limits, and all 8 ERP tool implementations.

## Requirements

### Requirement: Tool schema definition in MCP native format
The system SHALL define all tool schemas using MCP native format (`name`, `description`, `inputSchema`) in `erp_app/tools.py`. LLM calls SHALL use `erp_app/tools_format.get_openai_tools()` to convert to OpenAI format. MCP service tools SHALL use `mcp_` prefix for tool names (e.g., `mcp_query_order`).

#### Scenario: Tool schemas passed to LLM
- **WHEN** agent calls LLM
- **THEN** tool schemas are converted to OpenAI format via `get_openai_tools()` and included in the tools parameter

#### Scenario: MCP service tool naming
- **WHEN** MCP service returns tool list via `tools/list`
- **THEN** each tool name SHALL have `mcp_` prefix (e.g., `mcp_query_order`)
- **AND** the system SHALL maintain alias mapping in `client_factory` to route calls without prefix

#### Scenario: Tool name alias resolution
- **WHEN** agent calls `execute_tool("query_order", {...})`
- **THEN** the system SHALL resolve `query_order` to `mcp_query_order` via alias mapping
- **AND** execute the tool on the MCP service

### Requirement: Tool registry maps names to implementations
The system SHALL maintain a `TOOL_REGISTRY` dictionary mapping tool name strings to their Python implementation functions in `erp_app/tools.py`, not in `app/tools.py`. The agent SHALL access tool execution via `app/erp_client.execute_tool()` which delegates to `erp_app/tools.execute_tool()`.

#### Scenario: Tool execution via registry
- **WHEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "123"})`
- **THEN** system routes to `erp_app.TOOL_REGISTRY["query_order"](order_id="123")` and returns the result

#### Scenario: Unknown tool returns error
- **WHEN** agent calls `erp_client.execute_tool("nonexistent_tool", {})`
- **THEN** system returns TOOL_NOT_FOUND error

### Requirement: Nine ERP tools implemented
The system SHALL implement exactly 9 tools: query_order, query_orders, query_inventory, query_supplier (SAFE); create_order (CAUTION); update_order, cancel_order, delete_order, adjust_inventory (DANGER). Tool implementations SHALL be defined in `erp_app/tools.py` and delegate to the service layer in `erp_app/services/`.

#### Scenario: query_order returns order details
- **WHEN** `erp_client.execute_tool("query_order", {"order_id": "123"})` is called
- **THEN** system returns order 123's full details from SQLite via order_service

#### Scenario: query_orders batch query
- **WHEN** query_orders(["123","124","125"]) is called
- **THEN** system returns details for all three orders

#### Scenario: query_inventory returns stock info
- **WHEN** query_inventory("iPhone-15") is called
- **THEN** system returns qty, reserved, available, reorder_point

#### Scenario: query_supplier returns supplier info
- **WHEN** query_supplier("SUP-A") is called
- **THEN** system returns supplier name, contact, items, lead_time_days

#### Scenario: create_order creates and returns new order
- **WHEN** `erp_client.execute_tool("create_order", {"type": "sales", "items": [{"sku": "iPhone-15", "qty": 2}], "customer": "张三"})` is called
- **THEN** system creates order with auto-incremented ID via order_service, sets status="pending", reserves inventory, and returns the new order

#### Scenario: update_order modifies order field
- **WHEN** `erp_client.execute_tool("update_order", {"order_id": "123", "field": "address", "value": "北京市朝阳区"})` is called after approval
- **THEN** system updates order 123's address and updated_at timestamp via order_service

#### Scenario: cancel_order cancels and releases inventory
- **WHEN** `erp_client.execute_tool("cancel_order", {"order_id": "124", "reason": "客户要求"})` is called after approval
- **THEN** system sets status="cancelled", cancel_reason via order_service, and releases reserved inventory

#### Scenario: delete_order removes cancelled order
- **WHEN** `erp_client.execute_tool("delete_order", {"order_id": "126"})` is called on a cancelled order after approval
- **THEN** system removes the order from database via order_service

#### Scenario: delete_order rejects non-cancelled order
- **WHEN** `erp_client.execute_tool("delete_order", {"order_id": "123"})` is called on a non-cancelled order
- **THEN** system returns DATA_CONFLICT error "仅可删除已取消的订单"

#### Scenario: adjust_inventory modifies stock quantity
- **WHEN** `erp_client.execute_tool("adjust_inventory", {"sku": "iPhone-15", "delta": -20, "reason": "盘点调整"})` is called after approval
- **THEN** system updates qty from 60 to 40 and recalculates available via inventory_service

### Requirement: Tool risk level configuration
The system SHALL define `TOOL_RISK_LEVELS` mapping each tool name to SAFE/CAUTION/DANGER in `erp_app/config.py`, configurable via config.py.

#### Scenario: Risk level lookup
- **WHEN** agent checks risk level for "update_order"
- **THEN** system returns "DANGER"

### Requirement: Tool quantity limits
The system SHALL define TOOL_LIMITS mapping each tool name to its limit configuration (max_items), enforced before CAUTION/DANGER tool execution.

#### Scenario: Create order within limit
- **WHEN** create_order with 3 items (max_items=5)
- **THEN** execution proceeds normally

#### Scenario: Create order exceeds limit
- **WHEN** create_order with 8 items (max_items=5)
- **THEN** system returns TOOL_LIMIT error "单次最多创建5条，当前请求8条，请分批操作"

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
