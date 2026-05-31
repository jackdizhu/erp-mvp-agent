## Purpose

Define the MCP Registry implementation that manages MCP client lifecycle, configuration loading, and service lookup for the Agent.

## Requirements

### Requirement: MCP Registry Configuration Loading
The MCP Registry SHALL load MCP server configurations from JSON config file.

#### Scenario: Load from JSON file
- **GIVEN** mcp_servers.json exists in config_dir
- **WHEN** the registry is initialized
- **THEN** the registry SHALL parse the JSON and create MCPClient instances

#### Scenario: Graceful fallback when config missing
- **GIVEN** mcp_servers.json does not exist
- **WHEN** the registry loads configuration
- **THEN** the registry SHALL log a warning and continue with empty client list

#### Scenario: JSON Schema validation
- **GIVEN** the config file has invalid format
- **WHEN** the registry validates the schema
- **THEN** the registry SHALL log an error and use graceful fallback

### Requirement: Service Registration
The MCP Registry SHALL register MCP clients by name.

#### Scenario: Register by name
- **GIVEN** an MCPClient is created
- **WHEN** register_client(name, client) is called
- **THEN** the client SHALL be stored by name for later retrieval

### Requirement: Service Lookup
The MCP Registry SHALL support looking up clients by name or tool prefix.

#### Scenario: Lookup by name
- **GIVEN** a client is registered as "erp"
- **WHEN** get_client("erp") is called
- **THEN** the registry SHALL return the registered MCPClient

#### Scenario: Lookup by tool prefix
- **GIVEN** a client has tool "mcp_query_order" registered
- **WHEN** get_client_for_tool("mcp_query_order") is called
- **THEN** the registry SHALL return the client that owns that tool

### Requirement: Runtime Hot Reload
The MCP Registry SHALL support runtime configuration reload without restart.

#### Scenario: Hot reload endpoint
- **GIVEN** POST /api/mcp/reload endpoint is called
- **WHEN** the reload is triggered
- **THEN** the registry SHALL diff the new config with current clients

#### Scenario: Add new client on reload
- **GIVEN** a new service is added to config
- **WHEN** reload is triggered
- **THEN** the registry SHALL create and register the new MCPClient

#### Scenario: Remove client on reload
- **GIVEN** a service is removed from config
- **WHEN** reload is triggered
- **THEN** the registry SHALL wait for in-flight calls to complete before removing

### Requirement: Tool Prefix Mapping
The MCP Registry SHALL map tools to clients based on tool name prefixes.

#### Scenario: Tool prefix registration
- **GIVEN** a client has tools with names starting with "mcp_"
- **WHEN** the client is registered
- **THEN** the registry SHALL map all tool names to this client