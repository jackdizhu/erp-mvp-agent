## Purpose

Define the detailed logging specification for MCP Client and MCP Service, enabling complete request/response tracing and debugging.

## ADDED Requirements

### Requirement: MCP Client _request() logging
The system SHALL log every HTTP request made by MCPClient with method, URL, request body, response, and duration in milliseconds.

#### Scenario: Log successful request
- **WHEN** `_request()` sends a POST request to `/mcp` with `method: "tools/list"`
- **THEN** the system logs a JSON record containing `timestamp`, `level: "INFO"`, `logger: "mcp_client"`, `method: "tools/list"`, `params: {}`, `result: {tools: [...]}`, `duration_ms: 25`

#### Scenario: Log failed request
- **WHEN** `_request()` receives a JSON-RPC error response
- **THEN** the system logs a JSON record containing `method`, `error: {code, message}`, `duration_ms`

### Requirement: MCP Client list_tools() logging
The system SHALL log the result of `list_tools()` call including the number of tools returned.

#### Scenario: Log list_tools result
- **WHEN** `list_tools()` successfully returns tool schemas
- **THEN** the system logs `method: "tools/list"`, `tools_count: 9`, `duration_ms`

### Requirement: MCP Client call_tool() logging
The system SHALL log the result of `call_tool()` call including tool name, arguments, and result/error.

#### Scenario: Log call_tool success
- **WHEN** `call_tool("query_order", {"order_id": "123"})` returns order data
- **THEN** the system logs `method: "tools/call"`, `tool: "query_order"`, `args: {"order_id": "123"}`, `duration_ms`

#### Scenario: Log call_tool error
- **WHEN** `call_tool("query_order", {"order_id": "999"})` raises TOOL_NOT_FOUND
- **THEN** the system logs `method: "tools/call"`, `tool: "query_order"`, `error: "Tool not found: query_order"`, `duration_ms`

### Requirement: MCP Service endpoint logging
The system SHALL log every request to `/mcp`, `/`, `/mcp/tools/list`, `/mcp/tools/call` endpoints with method, params, response status, and duration.

#### Scenario: Log /mcp endpoint request
- **WHEN** `POST /mcp` receives `{"method": "initialize", "params": {...}}`
- **THEN** the system logs `endpoint: "/mcp"`, `method: "initialize"`, `params: {...}`, `status: 200`, `duration_ms: 5`

#### Scenario: Log / endpoint request
- **WHEN** `POST /` receives `{"method": "tools/list", "params": {}}`
- **THEN** the system logs `endpoint: "/"`, `method: "tools/list"`, `status: 200`, `duration_ms: 10`

### Requirement: MCP Service _dispatch_method() logging
The system SHALL log the method dispatch and execution result in `_dispatch_method()`.

#### Scenario: Log method dispatch
- **WHEN** `_dispatch_method("tools/list", {}, "req-123")` is called
- **THEN** the system logs `method: "tools/list"`, `request_id: "req-123"`, `result: {tools: [...]}`, `duration_ms`

### Requirement: Log format structure
The system SHALL use structured JSON log format containing timestamp, level, logger name, method, params/args, result/error, and duration_ms.

#### Scenario: JSON log format
- **WHEN** any MCP logging occurs
- **THEN** the log output is valid JSON with fields: `timestamp` (ISO format), `level`, `logger`, `method`, `params`, `result` or `error`, `duration_ms`