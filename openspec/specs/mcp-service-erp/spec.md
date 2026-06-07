## Purpose

Define the ERP MCP Service that exposes ERP tool capabilities via MCP Protocol over HTTP, replacing the internal module import pattern.

## Requirements

### Requirement: MCP Service HTTP Server
The system SHALL implement an MCP Service HTTP Server in `erp_mcp_service/` that exposes `/mcp/*` endpoints.

#### Scenario: MCP Service health check
- **WHEN** GET `/health` is called
- **THEN** returns `{"status": "healthy", "service": "erp-mcp-service"}`

#### Scenario: MCP Service starts on configured port
- **WHEN** MCP Service is started with PORT=8001
- **THEN** the server listens on port 8001

### Requirement: POST /mcp/tools/list endpoint
The system SHALL expose a POST endpoint at `/mcp/tools/list` that returns all available tool schemas in MCP format.

#### Scenario: List all tools
- **WHEN** POST `/mcp/tools/list` is called with valid API Key
- **THEN** returns JSON-RPC response with tools array containing all 9 ERP tool schemas

#### Scenario: List tools without authentication
- **WHEN** POST `/mcp/tools/list` is called without API Key
- **THEN** returns 401 Unauthorized

#### Scenario: List tools with invalid API Key
- **WHEN** POST `/mcp/tools/list` is called with invalid API Key
- **THEN** returns 401 Unauthorized

### Requirement: POST /mcp/tools/call endpoint
The system SHALL expose a POST endpoint at `/mcp/tools/call` that executes tools and returns results.

#### Scenario: Execute query_order tool
- **WHEN** POST `/mcp/tools/call` with `{"name": "mcp_query_order", "arguments": {"order_id": "123"}}` is called
- **THEN** the system executes the corresponding tool via erp_app and returns result

#### Scenario: Execute with invalid tool name
- **WHEN** POST `/mcp/tools/call` with unknown tool name
- **THEN** returns JSON-RPC error with code -32601 (Method not found)

#### Scenario: Execute with missing parameters
- **WHEN** POST `/mcp/tools/call` with incomplete arguments
- **THEN** returns JSON-RPC error with code -32602 (Invalid params)

### Requirement: API Key authentication middleware
The system SHALL implement API Key authentication middleware that validates X-API-Key header.

#### Scenario: Valid API Key passes
- **WHEN** request includes `X-API-Key: correct-key`
- **THEN** the request is processed

#### Scenario: Missing API Key rejected
- **WHEN** request does not include X-API-Key header
- **THEN** returns 401 with body `{"error": "Missing API Key"}`

### Requirement: MCP Service reuses erp_app core logic
The system SHALL delegate tool execution to existing `erp_app/tools.py` functions without duplicating business logic.

#### Scenario: Tool execution delegates to erp_app
- **WHEN** `/mcp/tools/call` executes create_order
- **THEN** system calls `erp_app.tools.execute_tool("create_order", args)`
- **AND** returns the same result format as direct erp_app call

### Requirement: JSON-RPC 2.0 compliant responses
The system SHALL return responses in JSON-RPC 2.0 format.

#### Scenario: Successful response format
- **WHEN** tool executes successfully
- **THEN** returns `{"jsonrpc": "2.0", "id": <request_id>, "result": <result>}`

#### Scenario: Error response format
- **WHEN** tool execution fails
- **THEN** returns `{"jsonrpc": "2.0", "id": <request_id>, "error": {"code": <code>, "message": <message>}}`

### Requirement: MCP Service Request Tracking
MCP 服务端 SHALL 从请求头提取 `X-Client-Id` 标识客户端来源，并在 Session 中维护 `pending_requests` 字典追踪未完成请求。响应 SHALL 严格回显请求 `id`。

#### Scenario: Server extracts client ID from header
- **WHEN** 服务端收到携带 `X-Client-Id` header 的请求
- **THEN** 将 client_id 关联到当前 session

#### Scenario: Server tracks pending requests per session
- **WHEN** 服务端收到 JSON-RPC 请求并开始处理
- **THEN** 将 request_id 记录到 session 的 pending_requests 中

#### Scenario: Server removes completed request from tracking
- **WHEN** 服务端返回 JSON-RPC 响应
- **THEN** 从 pending_requests 中移除对应 request_id

### Requirement: MCP /mcp Endpoint
The MCP Service SHALL implement POST /mcp endpoint for MCP protocol messages.

#### Scenario: Initialize request
- **GIVEN** POST /mcp is called with initialize method
- **WHEN** authentication succeeds
- **THEN** the server SHALL return protocol version and server capabilities

#### Scenario: Invalid JSON-RPC version
- **GIVEN** the request has jsonrpc "1.0"
- **WHEN** the server processes the initialize request
- **THEN** the server SHALL return JSON-RPC error -32600

#### Scenario: Notifications/initialized
- **GIVEN** POST /mcp is called with notifications/initialized method
- **WHEN** the server processes the notification
- **THEN** the server SHALL return 202 Accepted

### Requirement: Tool Schema Metadata Extension
The system SHALL extend tool schemas with risk metadata fields for approval flow integration.

#### Scenario: DANGER tool with metadata
- **WHEN** tools/list is called
- **THEN** each tool includes metadata block:
  ```json
  {
    "name": "mcp_update_order",
    "metadata": {
      "riskLevel": "DANGER",
      "requiresApproval": true,
      "irreversible": false,
      "approvalSummary": "修改订单{order_id}的{field}"
    }
  }
  ```

#### Scenario: Tool risk levels
| Tool | riskLevel | requiresApproval | irreversible |
|------|-----------|------------------|--------------|
| query_* | SAFE | false | false |
| create_order | WARNING | false | false |
| update_order | DANGER | true | false |
| cancel_order | DANGER | true | false |
| delete_order | DANGER | true | true |
| adjust_inventory | DANGER | true | false |

### Requirement: Approval Interception for High-Risk Tools
The system SHALL intercept tool calls that require approval and return pending status instead of executing.

#### Scenario: DANGER tool returns pending
- **WHEN** `tools/call` is invoked with `mcp_update_order(order_id="ORD-001", field="address", value="北京")`
- **AND** tool has `requiresApproval: true`
- **THEN** system returns:
  ```json
  {
    "status": "PENDING",
    "action_id": "act_<12 hex chars>",
    "tool": "update_order",
    "args": {"order_id": "ORD-001", "field": "address", "value": "北京"},
    "risk_level": "DANGER",
    "title": "修改订单",
    "summary": "修改订单 ORD-001 的 address",
    "description": "将订单 ORD-001 的地址从'旧地址'修改为'北京'",
    "warning": null,
    "detail": {...},
    "expires_at": 1717200000.0,
    "ttl_seconds": 300
  }
  ```

### Requirement: mcp_confirm_approval Tool
The system SHALL provide mcp_confirm_approval tool for confirming or rejecting pending actions.

#### Scenario: Confirm pending action
- **WHEN** `mcp_confirm_approval(action_id="act_abc123", approved=true)` is called
- **AND** action status is "pending"
- **AND** action is not expired
- **THEN** execute original tool, return:
  ```json
  {
    "success": true,
    "action_id": "act_abc123",
    "executed": true,
    "result": {"success": true, "data": {...}}
  }
  ```

#### Scenario: Reject pending action
- **WHEN** `mcp_confirm_approval(action_id="act_abc123", approved=false)` is called
- **THEN** mark action as rejected, return:
  ```json
  {
    "success": true,
    "action_id": "act_abc123",
    "executed": false,
    "message": "操作已取消"
  }
  ```

#### Scenario: Expired action confirmation
- **WHEN** confirm is called for expired action
- **THEN** return:
  ```json
  {
    "success": false,
    "error": "APPROVAL_EXPIRED",
    "message": "审批已过期，请重新发起操作"
  }
  ```

### Requirement: ApprovalManager for Pending Actions
The system SHALL implement ApprovalManager class to manage pending action lifecycle.

#### Scenario: Create pending action
- **WHEN** ApprovalManager.create() is called with tool_name, arguments, risk_level, approval_detail, ttl
- **THEN** returns PendingAction with unique action_id and "pending" status

#### Scenario: Concurrent pending actions
- **WHEN** multiple DANGER tools are called in sequence
- **THEN** each creates independent pending action with unique action_id

### Requirement: Approval Configuration
The system SHALL support configurable TTL and max pending actions.

| Key | Default | Description |
|-----|---------|-------------|
| APPROVAL_TTL | 300 | Seconds until pending action expires |
| APPROVAL_MAX_PENDING | 10 | Maximum concurrent pending actions |

### Requirement: Approval Error Codes
The system SHALL return specific error codes for approval operations.

| Code | Meaning |
|------|---------|
| ACTION_NOT_FOUND | action_id does not exist |
| ACTION_ALREADY_PENDING | Action already in pending state |
| ACTION_ALREADY_APPROVED | Action already approved |
| ACTION_ALREADY_REJECTED | Action already rejected |
| APPROVAL_EXPIRED | Action TTL exceeded |
| MAX_PENDING_EXCEEDED | Too many pending actions |
| MISSING_ACTION_ID | action_id parameter missing |