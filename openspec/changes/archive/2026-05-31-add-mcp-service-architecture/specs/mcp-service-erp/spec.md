## Purpose

Define the ERP MCP Service that exposes ERP tool capabilities via MCP Protocol over HTTP, replacing the internal module import pattern.

## ADDED Requirements

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
- **WHEN** POST `/mcp/tools/call` with `{"name": "erp_query_order", "arguments": {"order_id": "123"}}` is called
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
