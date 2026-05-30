## Purpose

Define the tool system including schema definitions, registry, risk levels, quantity limits, and all 8 ERP tool implementations.

## Requirements

### Requirement: Tool schema definition in OpenAI format
The system SHALL define all tool schemas using OpenAI's function calling format (type="function", function with name/description/parameters) in `erp_app/tools.py`, and the agent SHALL obtain schemas via `erp_client.get_tools()` instead of importing `TOOL_SCHEMAS` directly. The schemas SHALL be passed to the LLM via the tools parameter.

#### Scenario: Tool schemas passed to LLM
- **WHEN** agent calls LLM
- **THEN** all 9 tool schemas are obtained via `erp_client.get_tools()` and included in the tools parameter

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
