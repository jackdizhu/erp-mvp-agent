# Delta Spec: mcp-agent-integration

## ADDED Requirements

### Requirement: Client Backend Configuration
The Agent SHALL support configurable client backend via CLIENT_BACKEND environment variable.

#### Scenario: ErpAdapter mode
- **GIVEN** CLIENT_BACKEND=erp_adapter
- **WHEN** the agent starts
- **THEN** the agent SHALL use only ErpAdapter for all tool calls

#### Scenario: MCP mode
- **GIVEN** CLIENT_BACKEND=mcp
- **WHEN** the agent starts
- **THEN** the agent SHALL use MCP client for tool calls

#### Scenario: Hybrid mode
- **GIVEN** CLIENT_BACKEND=hybrid
- **WHEN** the agent starts
- **THEN** the agent SHALL attempt MCP first, fallback to ErpAdapter on failure

### Requirement: ClientFactory Integration
The Agent SHALL use ClientFactory as the unified interface for all client operations.

#### Scenario: Get tools from factory
- **GIVEN** multiple clients are registered
- **WHEN** get_all_tools() is called
- **THEN** the factory SHALL return tools from all registered clients

#### Scenario: Execute tool via factory
- **WHEN** execute_tool(tool_name, args) is called
- **THEN** the factory SHALL route to appropriate client and return result

#### Scenario: Fallback on MCP failure
- **GIVEN** hybrid mode is enabled
- **WHEN** MCP client fails with recoverable error
- **THEN** the factory SHALL fallback to ErpAdapter automatically

### Requirement: MCP Error Propagation
The Agent SHALL propagate MCP errors to the frontend for display.

#### Scenario: Stream error with MCP code
- **GIVEN** an MCP error occurs during streaming
- **WHEN** the error is propagated to frontend
- **THEN** the frontend SHALL display MCP error notification

#### Scenario: Error recovery suggestion
- **GIVEN** a recoverable MCP error occurs
- **WHEN** the error is displayed
- **THEN** the message SHALL indicate the error is temporary

### Requirement: LLM Timeout Configuration
The Agent SHALL use configurable LLM timeout from TIMEOUT_CONFIG.

#### Scenario: Custom LLM timeout
- **GIVEN** LLM_TIMEOUT environment variable is set
- **WHEN** the agent makes an LLM call
- **THEN** the timeout SHALL use the configured value