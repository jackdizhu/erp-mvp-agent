## Purpose

Define the environment variable override mechanism for MCP service configuration, enabling flexible deployment without modifying JSON config files.

## ADDED Requirements

### Requirement: MCP_SERVICE_URL environment variable override
The system SHALL support a `MCP_SERVICE_URL` environment variable that overrides the URL in `mcp_servers.json` for the ERP MCP service. When set, the registry SHALL use this URL instead of the JSON config value.

#### Scenario: Environment variable overrides JSON config
- **WHEN** `MCP_SERVICE_URL=http://localhost:9001/mcp` is set and `mcp_servers.json` contains `"url": "http://localhost:8001"`
- **THEN** the registry creates MCPClient with endpoint `http://localhost:9001/mcp`

#### Scenario: Environment variable not set, JSON config used
- **WHEN** `MCP_SERVICE_URL` is not set and `mcp_servers.json` contains `"url": "http://localhost:9001/mcp"`
- **THEN** the registry creates MCPClient with endpoint `http://localhost:9001/mcp`

#### Scenario: Environment variable set to empty string
- **WHEN** `MCP_SERVICE_URL=""` is set (empty string)
- **THEN** the registry falls back to the JSON config URL

### Requirement: MCP_SERVICE_PORT default changed to 9001
The system SHALL default `MCP_SERVICE_PORT` to `9001` instead of `8001`, configurable via the `MCP_SERVICE_PORT` environment variable.

#### Scenario: Default port is 9001
- **WHEN** `MCP_SERVICE_PORT` environment variable is not set
- **THEN** the MCP Service starts on port 9001

#### Scenario: Custom port via environment variable
- **WHEN** `MCP_SERVICE_PORT=8080` is set
- **THEN** the MCP Service starts on port 8080

### Requirement: MCP_SERVICE_URL logged at startup
The system SHALL log the actual MCP service URL being used (from environment variable or JSON config) at INFO level during registry initialization.

#### Scenario: URL logged when from environment variable
- **WHEN** `MCP_SERVICE_URL=http://localhost:9001/mcp` is set
- **THEN** the registry logs `MCP service URL from env: http://localhost:9001/mcp`

#### Scenario: URL logged when from JSON config
- **WHEN** `MCP_SERVICE_URL` is not set
- **THEN** the registry logs `MCP service URL from config: http://localhost:9001/mcp`

### Requirement: mcp_servers.json default URL updated
The `mcp_servers.json` default configuration SHALL use `http://localhost:9001/mcp` as the ERP service URL.

#### Scenario: Default config points to new port and path
- **WHEN** `mcp_servers.json` is loaded without modifications
- **THEN** the erp service URL is `http://localhost:9001/mcp`
