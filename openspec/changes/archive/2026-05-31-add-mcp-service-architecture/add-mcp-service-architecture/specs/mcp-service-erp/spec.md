# Delta Spec: mcp-service-erp

## ADDED Requirements

### Requirement: MCP HTTP Server
The MCP Service SHALL implement an HTTP server using FastAPI.

#### Scenario: FastAPI server
- **GIVEN** the MCP service is started
- **WHEN** HTTP requests are received
- **THEN** the server SHALL route requests to appropriate handlers

### Requirement: Health Check Endpoint
The MCP Service SHALL provide a health check endpoint.

#### Scenario: Health check
- **GIVEN** GET /health is called
- **WHEN** the server is running
- **THEN** the server SHALL return {"status": "healthy"}

### Requirement: Tools List Endpoint
The MCP Service SHALL provide tools/list endpoint returning JSON-RPC 2.0 response.

#### Scenario: List tools
- **GIVEN** POST /mcp/tools/list is called with valid JSON-RPC request
- **WHEN** authentication succeeds
- **THEN** the server SHALL return JSON-RPC 2.0 response with tools list

#### Scenario: Invalid JSON-RPC version
- **GIVEN** the request has jsonrpc "1.0"
- **WHEN** the server processes the request
- **THEN** the server SHALL return JSON-RPC error -32600

### Requirement: Tools Call Endpoint
The MCP Service SHALL provide tools/call endpoint for tool execution.

#### Scenario: Call existing tool
- **GIVEN** POST /mcp/tools/call is called with valid tool name and arguments
- **WHEN** authentication succeeds and tool exists
- **THEN** the server SHALL delegate to erp_app/tools.py and return result

#### Scenario: Call non-existent tool
- **GIVEN** POST /mcp/tools/call is called with unknown tool name
- **WHEN** the server processes the request
- **THEN** the server SHALL return JSON-RPC error -32601

#### Scenario: Missing required parameters
- **GIVEN** POST /mcp/tools/call is called with missing arguments
- **WHEN** the server validates the request
- **THEN** the server SHALL return JSON-RPC error -32602

### Requirement: API Key Authentication
The MCP Service SHALL authenticate requests using API Key header.

#### Scenario: Valid API key
- **GIVEN** X-API-Key header matches configured key
- **WHEN** a protected endpoint is called
- **THEN** the request SHALL be processed

#### Scenario: Missing API key
- **GIVEN** no X-API-Key header is provided
- **WHEN** a protected endpoint is called
- **THEN** the server SHALL return 401 Unauthorized

#### Scenario: Invalid API key
- **GIVEN** X-API-Key header does not match
- **WHEN** a protected endpoint is called
- **THEN** the server SHALL return 401 Unauthorized

### Requirement: JSON-RPC Error Response
The MCP Service SHALL return proper JSON-RPC 2.0 error responses.

#### Scenario: Error response format
- **GIVEN** an error occurs during request processing
- **WHEN** the server generates an error response
- **THEN** the response SHALL follow JSON-RPC 2.0 error format: {"jsonrpc": "2.0", "error": {"code": N, "message": "..."}}