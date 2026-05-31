## Purpose

Define the MCP Client implementation that enables the Agent to communicate with MCP Services via HTTP/JSON-RPC 2.0 protocol.

## ADDED Requirements

### Requirement: MCPClient HTTP implementation
The system SHALL implement an `MCPClient` class in `app/clients/mcp_client.py` that communicates with MCP Services via HTTP POST + JSON-RPC 2.0.

#### Scenario: Initialize MCPClient with endpoint
- **WHEN** `MCPClient("http://localhost:8001")` is instantiated
- **THEN** the client stores the base URL and default timeout settings

#### Scenario: List available tools
- **WHEN** `mcp_client.list_tools()` is called
- **THEN** the system sends POST to `/mcp/tools/list` with JSON-RPC request
- **AND** returns the list of tool schemas from MCP Service

#### Scenario: Call tool execution
- **WHEN** `mcp_client.call_tool("erp_query_order", {"order_id": "123"})` is called
- **THEN** the system sends POST to `/mcp/tools/call` with JSON-RPC request
- **AND** returns the tool execution result

#### Scenario: Handle MCP service unavailable
- **WHEN** MCP Service returns connection error or 503
- **THEN** the system raises MCPServiceUnavailable error with error code MCP_SERVICE_UNAVAILABLE

### Requirement: MCPClient API Key authentication
The system SHALL add API Key header to all MCP requests when configured.

#### Scenario: Authenticated request
- **WHEN** MCPClient is configured with api_key="secret-key-123"
- **THEN** all requests include header `X-API-Key: secret-key-123`

#### Scenario: Request without API Key
- **WHEN** MCPClient is configured without api_key
- **THEN** requests are sent without X-API-Key header

#### Scenario: API Key from config
- **WHEN** `MCPClient` is initialized without explicit api_key
- **THEN** client reads from `config.MCP_SERVICE_CONFIG["erp"]["api_key"]`
- **AND** uses environment variable `MCP_API_KEY` as fallback

#### Scenario: API Key missing in all sources
- **WHEN** api_key not provided, config key missing, env var not set
- **THEN** MCPClient proceeds without authentication header
- **AND** logs warning "API Key not configured, using unauthenticated mode"

### Requirement: Configurable timeout
The system SHALL support configurable timeout for MCP requests.

#### Scenario: Custom timeout
- **WHEN** `MCPClient(endpoint, timeout=20)` is instantiated
- **THEN** HTTP requests timeout after 20 seconds

### Requirement: MCPClient error handling
The system SHALL catch MCP-specific errors and convert to AgentError types.

#### Scenario: Connection timeout
- **WHEN** MCP Service does not respond within timeout
- **THEN** system raises MCPConnectionError with code SYS_TIMEOUT

#### Scenario: Invalid JSON-RPC response
- **WHEN** MCP Service returns malformed JSON-RPC response
- **THEN** system raises MCPInvalidResponse with code LLM_INVALID_RESPONSE

#### Scenario: Tool not found in MCP
- **WHEN** `call_tool` is called with unknown tool name
- **THEN** system raises MCPToolNotFound with code TOOL_NOT_FOUND

### Requirement: MCPRegistry JSON configuration loading
The system SHALL implement `MCPRegistry` in `app/clients/mcp_registry.py` that loads MCP service configuration from `app/config_dir/mcp_servers.json`.

#### Scenario: Load configuration at startup
- **WHEN** Agent starts and `MCPRegistry.initialize()` is called
- **THEN** registry reads `app/config_dir/mcp_servers.json`
- **AND** creates MCPClient instance for each entry in `mcpServers`
- **AND** registers all discovered tools with ClientFactory

#### Scenario: Configuration file missing
- **WHEN** `mcp_servers.json` does not exist in config_dir
- **THEN** registry logs warning "mcp_servers.json not found, no MCP services registered"
- **AND** Agent continues with local erp_adapter only

#### Scenario: Configuration file with invalid JSON
- **WHEN** `mcp_servers.json` contains invalid JSON syntax
- **THEN** registry raises MCPConfigError with details of parse failure
- **AND** Agent falls back to local erp_adapter

#### Scenario: Service entry with unsupported type
- **WHEN** a service entry has `type` other than `streamableHttp`
- **THEN** registry logs warning "Unsupported type '<type>' for service '<name>', skipping"
- **AND** other services are still registered normally

#### Scenario: Service entry with missing required fields
- **WHEN** a service entry is missing `url` field
- **THEN** registry logs warning "Missing required field 'url' for service '<name>', skipping"
- **AND** other services are still registered normally

### Requirement: MCPRegistry runtime hot-reload
The system SHALL support runtime configuration reload via `POST /api/mcp/reload` endpoint.

#### Scenario: Reload with added service
- **WHEN** `POST /api/mcp/reload` is called and new service entry exists in updated JSON
- **THEN** registry creates new MCPClient for added service
- **AND** returns `{"added": 1, "removed": 0, "updated": 0}`

#### Scenario: Reload with removed service
- **WHEN** a service entry is removed from updated JSON
- **THEN** registry waits for in-flight calls to complete, then removes client
- **AND** returns `{"added": 0, "removed": 1, "updated": 0}`

#### Scenario: Reload with updated service config
- **WHEN** a service entry has changed `url`, `headers`, or `timeout`
- **THEN** registry rebuilds MCPClient with new configuration
- **AND** returns `{"added": 0, "removed": 0, "updated": 1}`

#### Scenario: Reload with failed client creation
- **WHEN** new service config has unreachable URL
- **THEN** registry logs error for failed service
- **AND** existing services remain unaffected
- **AND** returns `{"added": 0, "removed": 0, "updated": 0, "failed": 1}`

### Requirement: MCPRegistry service lookup
The system SHALL provide service lookup by name and tool prefix.

#### Scenario: Lookup by service name
- **WHEN** `registry.get_client("erp")` is called
- **THEN** returns MCPClient instance for the "erp" service

#### Scenario: Lookup by tool name prefix
- **WHEN** `registry.get_client_for_tool("erp_query_order")` is called
- **THEN** returns MCPClient instance for the service whose tools match prefix "erp_"

#### Scenario: Lookup for unknown service
- **WHEN** `registry.get_client("unknown")` is called
- **THEN** returns None
