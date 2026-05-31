# Delta Spec: mcp-client

## ADDED Requirements

### Requirement: MCP Client HTTP/JSON-RPC 2.0 Support
The MCP Client SHALL support HTTP/JSON-RPC 2.0 protocol for communicating with MCP services.

#### Scenario: JSON-RPC request/response
- **GIVEN** an MCP service endpoint is configured
- **WHEN** the client sends a JSON-RPC request
- **THEN** the server SHALL return a valid JSON-RPC 2.0 response

#### Scenario: SSE response handling
- **GIVEN** an MCP service returns text/event-stream response
- **WHEN** the client receives the response
- **THEN** the client SHALL parse the SSE data payload

### Requirement: API Key Authentication
The MCP Client SHALL support API Key authentication via headers.

#### Scenario: API Key in headers
- **GIVEN** API Key is configured
- **WHEN** the client makes a request
- **THEN** the client SHALL include the API Key in the X-API-Key header

### Requirement: Configurable Timeout
The MCP Client SHALL support configurable request timeouts.

#### Scenario: Custom timeout
- **GIVEN** a timeout value is configured
- **WHEN** the request takes longer than the timeout
- **THEN** the client SHALL raise a MCP_CONNECTION_TIMEOUT error

### Requirement: Error Handling
The MCP Client SHALL translate MCP errors into AgentError instances.

#### Scenario: Service unavailable
- **GIVEN** the MCP service returns 503
- **WHEN** the client processes the response
- **THEN** the client SHALL raise MCP_SERVICE_UNAVAILABLE error

#### Scenario: Authentication failure
- **GIVEN** the MCP service returns 401
- **WHEN** the client processes the response
- **THEN** the client SHALL raise MCP_AUTH_FAILED error

#### Scenario: Tool not found
- **GIVEN** the MCP service returns error code -32601
- **WHEN** the client processes the error
- **THEN** the client SHALL raise MCP_TOOL_NOT_FOUND error

### Requirement: Protocol Initialization
The MCP Client SHALL perform MCP protocol initialization before first tool call.

#### Scenario: Initialize handshake
- **GIVEN** the client is created with endpoint and headers
- **WHEN** the first tool operation is requested
- **THEN** the client SHALL send initialize request and handle notifications/initialized

### Requirement: Tool Listing
The MCP Client SHALL fetch and cache the list of available tools from the MCP service.

#### Scenario: List tools
- **GIVEN** the client is initialized
- **WHEN** list_tools() is called
- **THEN** the client SHALL return tools from the MCP service result

### Requirement: Tool Execution
The MCP Client SHALL execute tools via the MCP service.

#### Scenario: Call tool
- **GIVEN** the client is initialized
- **WHEN** call_tool(tool_name, arguments) is called
- **THEN** the client SHALL send the tool call request and return the result