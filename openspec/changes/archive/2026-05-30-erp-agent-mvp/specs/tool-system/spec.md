## ADDED Requirements

### Requirement: Tool schema definition in OpenAI format
The system SHALL define all tool schemas using OpenAI's function calling format (type="function", function with name/description/parameters), and pass them to the LLM via the tools parameter.

#### Scenario: Tool schemas passed to LLM
- **WHEN** agent calls LLM
- **THEN** all 8 tool schemas are included in the tools parameter with proper name, description, and JSON Schema parameters

### Requirement: Tool registry maps names to implementations
The system SHALL maintain a TOOL_REGISTRY dictionary mapping tool name strings to their Python implementation functions, and a TOOL_SCHEMAS list for LLM consumption.

#### Scenario: Tool execution via registry
- **WHEN** agent receives tool_call with name="query_order" and args={"order_id": "123"}
- **THEN** system calls TOOL_REGISTRY["query_order"](order_id="123") and returns the result

#### Scenario: Unknown tool returns error
- **WHEN** agent receives tool_call with name="nonexistent_tool"
- **THEN** system returns TOOL_NOT_FOUND error

### Requirement: Eight ERP tools implemented
The system SHALL implement exactly 8 tools: query_order, query_orders, query_inventory, query_supplier (SAFE); create_order (CAUTION); update_order, cancel_order, delete_order, adjust_inventory (DANGER).

#### Scenario: query_order returns order details
- **WHEN** query_order("123") is called
- **THEN** system returns order 123's full details from mock ERP

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
- **WHEN** create_order(type="sales", items=[{sku:"iPhone-15", qty:2}], customer="张三") is called
- **THEN** system creates order with auto-incremented ID, sets status="pending", reserves inventory, and returns the new order

#### Scenario: update_order modifies order field
- **WHEN** update_order("123", "address", "北京市朝阳区") is called after approval
- **THEN** system updates order 123's address and updated_at timestamp

#### Scenario: cancel_order cancels and releases inventory
- **WHEN** cancel_order("124", reason="客户要求") is called after approval
- **THEN** system sets status="cancelled", cancel_reason, and releases reserved inventory

#### Scenario: delete_order removes cancelled order
- **WHEN** delete_order("126") is called on a cancelled order after approval
- **THEN** system removes the order from data store

#### Scenario: delete_order rejects non-cancelled order
- **WHEN** delete_order("123") is called on a non-cancelled order
- **THEN** system returns DATA_CONFLICT error "仅可删除已取消的订单"

#### Scenario: adjust_inventory modifies stock quantity
- **WHEN** adjust_inventory("iPhone-15", delta=-20, reason="盘点调整") is called after approval
- **THEN** system updates qty from 60 to 40 and recalculates available

### Requirement: Tool risk level configuration
The system SHALL define TOOL_RISK_LEVELS mapping each tool name to SAFE/CAUTION/DANGER, configurable via config.py.

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
