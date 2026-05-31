## Purpose

Define the error handling for MCP service unavailability, ensuring clear error messages are returned to the frontend.

## ADDED Requirements

### Requirement: MCP Service Unavailable error code
The system SHALL define `MCP_SERVICE_UNAVAILABLE` error code for MCP service connection failures.

#### Scenario: MCP service connection refused
- **WHEN** Agent attempts to connect to MCP Service that is not running
- **THEN** system returns AgentError with code MCP_SERVICE_UNAVAILABLE, message "ERP服务暂时不可用，请稍后重试"

#### Scenario: MCP service returns 503
- **WHEN** MCP Service returns HTTP 503 Service Unavailable
- **THEN** system returns AgentError with code MCP_SERVICE_UNAVAILABLE, recoverable=false

### Requirement: Frontend error display
The system SHALL include MCP service errors in API response for frontend display.

#### Scenario: Error in chat response
- **WHEN** MCP service unavailable error occurs during chat
- **THEN** response includes `{"error": {"code": "MCP_SERVICE_UNAVAILABLE", "message": "ERP服务暂时不可用，请稍后重试", "recoverable": true}}`

#### Scenario: Error in streaming response
- **WHEN** MCP service unavailable error occurs during streaming chat
- **THEN** final `done` event includes error object with code MCP_SERVICE_UNAVAILABLE

### Requirement: MCP error codes taxonomy
The system SHALL define MCP-specific error codes.

#### Scenario: MCP_CONNECTION_TIMEOUT
- **WHEN** MCP Service connection times out
- **THEN** system returns error with code MCP_CONNECTION_TIMEOUT, source="system"

#### Scenario: MCP_INVALID_RESPONSE
- **WHEN** MCP Service returns invalid JSON-RPC response
- **THEN** system returns error with code MCP_INVALID_RESPONSE, source="llm"

#### Scenario: MCP_TOOL_NOT_FOUND
- **WHEN** MCP Service reports tool not found
- **THEN** system returns error with code MCP_TOOL_NOT_FOUND, source="tool"

#### Scenario: MCP_AUTH_FAILED
- **WHEN** MCP Service returns 401 Unauthorized
- **THEN** system returns error with code MCP_AUTH_FAILED, source="system", recoverable=false

### Requirement: Error is logged with context
The system SHALL log MCP errors with service endpoint and error details for debugging.

#### Scenario: Error logging
- **WHEN** MCP service error occurs
- **THEN** log entry includes MCP endpoint URL, error code, and original exception message
