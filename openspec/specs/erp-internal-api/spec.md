## Purpose

Define the internal HTTP API endpoints exposed by the erp_app package, mounted at `/erp` prefix on the main FastAPI application, for future independent service deployment.

## Requirements

### Requirement: GET /erp/tools/schemas endpoint
The system SHALL expose a GET endpoint at `/erp/tools/schemas` that returns the complete list of TOOL_SCHEMAS in OpenAI function calling format.

#### Scenario: Retrieve all tool schemas
- **WHEN** GET /erp/tools/schemas is called
- **THEN** the system returns an array of 9 tool schema objects with type, function name, description, and parameters

### Requirement: POST /erp/tools/execute endpoint
The system SHALL expose a POST endpoint at `/erp/tools/execute` that accepts `{tool_name, args}` and executes the corresponding tool, returning the result dict.

#### Scenario: Execute query tool
- **WHEN** POST /erp/tools/execute with `{tool_name: "query_order", args: {order_id: "123"}}` is called
- **THEN** the system returns `{"success": true, "data": <order details>}`

#### Scenario: Execute with invalid tool name
- **WHEN** POST /erp/tools/execute with `{tool_name: "unknown", args: {}}` is called
- **THEN** the system returns an error response with code TOOL_NOT_FOUND

#### Scenario: Execute with invalid parameters
- **WHEN** POST /erp/tools/execute with `{tool_name: "query_order", args: {}}` (missing order_id)
- **THEN** the system returns an error response with code TOOL_INVALID_PARAM

### Requirement: POST /erp/approval/detail endpoint
The system SHALL expose a POST endpoint at `/erp/approval/detail` that accepts `{tool_name, args}` and returns the approval detail object containing action_type, fields array, and irreversible flag.

#### Scenario: Get approval detail for cancel_order
- **WHEN** POST /erp/approval/detail with `{tool_name: "cancel_order", args: {order_id: "124"}}` is called
- **THEN** the system returns detail with fields=[{name:"操作类型",value:"取消订单"},{name:"订单编号",value:"124"},{name:"当前状态",value:"pending"},{name:"取消原因",value:""}]

#### Scenario: Get approval detail for irreversible operation
- **WHEN** POST /erp/approval/detail with `{tool_name: "delete_order", args: {order_id: "125"}}` is called
- **THEN** the response includes `irreversible: true`
