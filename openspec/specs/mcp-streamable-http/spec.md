## Purpose

Define the MCP Streamable HTTP transport layer implementation for the ERP MCP Service, ensuring compliance with the MCP specification (2025-03-26).

## Requirements

### Requirement: Single MCP endpoint with method dispatch
The system SHALL provide a single HTTP endpoint at `/mcp` that accepts POST requests and dispatches based on the JSON-RPC `method` field. The system SHALL also register the same handler at `/` for IDE compatibility.

#### Scenario: IDE connects to root path
- **WHEN** IDE MCP client sends `POST /` with `method: "initialize"`
- **THEN** the system processes the request and returns the initialize response

#### Scenario: Client connects to /mcp path
- **WHEN** client sends `POST /mcp` with `method: "tools/list"`
- **THEN** the system processes the request and returns the tools list

#### Scenario: Unknown method returns JSON-RPC error
- **WHEN** client sends `POST /mcp` with `method: "unknown/method"`
- **THEN** the system returns `{"jsonrpc":"2.0","id":"...","error":{"code":-32601,"message":"Method not found: unknown/method"}}`

### Requirement: Initialize handshake
The system SHALL handle the `initialize` method by returning server capabilities, protocol version, and server info. The response SHALL include `protocolVersion: "2025-03-26"`, `capabilities.tools`, and `serverInfo`.

#### Scenario: Successful initialize with full params
- **WHEN** client sends `POST /mcp` with `method: "initialize"` and `params.protocolVersion: "2025-03-26"` and `params.capabilities` and `params.clientInfo`
- **THEN** the system returns `{"jsonrpc":"2.0","id":"...","result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{"listChanged":false},"resources":{},"prompts":{},"logging":{}},"serverInfo":{"name":"erp-mcp-service","version":"1.0.0"},"instructions":"ERP MCP Service for inventory, order, and supplier management"}}`

#### Scenario: Initialize with minimal params
- **WHEN** client sends `POST /mcp` with `method: "initialize"` and empty params
- **THEN** the system still returns a valid initialize response with default values

#### Scenario: Initialize with unsupported protocol version
- **WHEN** client sends `POST /mcp` with `method: "initialize"` and `params.protocolVersion: "1.0.0"`
- **THEN** the system returns `{"jsonrpc":"2.0","id":"...","error":{"code":-32602,"message":"Unsupported protocol version","data":{"supported":["2025-03-26"],"requested":"1.0.0"}}}`

### Requirement: Server capabilities declaration
The system SHALL declare its capabilities in the initialize response, including tools, resources, prompts, and logging. For each capability category, the system SHALL indicate sub-capabilities like `listChanged`.

#### Scenario: Server declares tools capability
- **WHEN** server processes initialize request
- **THEN** the response includes `capabilities.tools` with `listChanged: false`

#### Scenario: Server includes optional instructions
- **WHEN** server processes initialize request
- **THEN** the response may include `instructions` field providing usage guidance

### Requirement: Notifications/initialized handling
The system SHALL handle `notifications/initialized` by returning HTTP 202 Accepted with no body, per MCP specification.

#### Scenario: Client sends initialized notification
- **WHEN** client sends `POST /mcp` with `method: "notifications/initialized"`
- **THEN** the system returns HTTP 202 with no response body

#### Scenario: Server rejects requests before initialized
- **WHEN** client sends `POST /mcp` with `method: "tools/list"` before sending `notifications/initialized`
- **THEN** the system may reject with error or process normally (stateless implementation does not enforce ordering)

### Requirement: Tools/list via unified endpoint
The system SHALL handle the `tools/list` method by returning the tool schemas in JSON-RPC result format, identical to the existing `/mcp/tools/list` route behavior.

#### Scenario: List tools via unified endpoint
- **WHEN** client sends `POST /mcp` with `method: "tools/list"`
- **THEN** the system returns `{"jsonrpc":"2.0","id":"...","result":{"tools":[...]}}` with all ERP tool schemas

### Requirement: Tools/call via unified endpoint
The system SHALL handle the `tools/call` method by executing the specified tool and returning the result in JSON-RPC format, identical to the existing `/mcp/tools/call` route behavior.

#### Scenario: Call tool via unified endpoint
- **WHEN** client sends `POST /mcp` with `method: "tools/call"` and `params.name: "query_order"` and `params.arguments: {"order_id": "123"}`
- **THEN** the system executes the tool and returns `{"jsonrpc":"2.0","id":"...","result":{...}}`

#### Scenario: Call nonexistent tool via unified endpoint
- **WHEN** client sends `POST /mcp` with `method: "tools/call"` and `params.name: "nonexistent"`
- **THEN** the system returns `{"jsonrpc":"2.0","id":"...","error":{"code":-32601,"message":"Tool not found: nonexistent"}}`

### Requirement: Protocol version header
The system SHALL include `MCP-Protocol-Version: 2025-03-26` in all JSON-RPC responses from the `/mcp` and `/` endpoints.

#### Scenario: Response includes protocol version header
- **WHEN** client sends any valid JSON-RPC request to `/mcp`
- **THEN** the response includes header `MCP-Protocol-Version: 2025-03-26`

### Requirement: Accept header validation
The system SHALL validate that incoming POST requests to `/mcp` and `/` include an `Accept` header containing both `application/json` and `text/event-stream`. If missing, the system SHALL return HTTP 400.

#### Scenario: Valid Accept header
- **WHEN** client sends `POST /mcp` with `Accept: application/json, text/event-stream`
- **THEN** the system processes the request normally

#### Scenario: Missing Accept header
- **WHEN** client sends `POST /mcp` without `Accept` header
- **THEN** the system returns HTTP 400 with error message about required Accept header

### Requirement: Deprecated legacy routes preserved
The system SHALL preserve the existing `/mcp/tools/list` and `/mcp/tools/call` routes for backward compatibility. These routes SHALL internally delegate to the same logic as the unified endpoint.

#### Scenario: Legacy tools/list still works
- **WHEN** client sends `POST /mcp/tools/list` with JSON-RPC body
- **THEN** the system returns the same response as the unified endpoint

#### Scenario: Legacy tools/call still works
- **WHEN** client sends `POST /mcp/tools/call` with JSON-RPC body
- **THEN** the system returns the same response as the unified endpoint

### Requirement: Version negotiation response
The system SHALL support version negotiation by returning the supported protocol version in the initialize response. If the client requests an unsupported version, the system SHALL return the latest supported version in the error response.

#### Scenario: Client requests current version
- **WHEN** client sends `params.protocolVersion: "2025-03-26"`
- **THEN** the system returns `protocolVersion: "2025-03-26"` in result

#### Scenario: Client requests unsupported version
- **WHEN** client sends `params.protocolVersion: "2024-11-05"` (older version)
- **THEN** the system SHOULD return `protocolVersion: "2025-03-26"` in result (server uses newer version)