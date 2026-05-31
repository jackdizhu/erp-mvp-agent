## Purpose

Define the configurable timeout settings for LLM calls and MCP service communications, supporting a default of 15 seconds for LLM calls.

## ADDED Requirements

### Requirement: Timeout configuration in config.py
The system SHALL define `TIMEOUT_CONFIG` in `app/config.py` with configurable timeout values.

#### Scenario: Default timeout values
- **WHEN** config.py is loaded without custom values
- **THEN** `TIMEOUT_CONFIG["llm_call"]` defaults to 15
- **AND** `TIMEOUT_CONFIG["mcp_request"]` defaults to 10
- **AND** `TIMEOUT_CONFIG["mcp_connect"]` defaults to 5

#### Scenario: Custom timeout via environment
- **WHEN** environment variable `LLM_TIMEOUT=20` is set
- **THEN** `TIMEOUT_CONFIG["llm_call"]` equals 20

### Requirement: LLM call respects timeout
The system SHALL pass timeout value to LLM API calls.

#### Scenario: LLM call with custom timeout
- **WHEN** `TIMEOUT_CONFIG["llm_call"]` is 20
- **AND** `call_llm()` is invoked
- **THEN** the LLM API request timeout is set to 20 seconds

#### Scenario: LLM timeout triggers error
- **WHEN** LLM API does not respond within configured timeout
- **THEN** system raises LLMTimeout error with code LLM_TIMEOUT

### Requirement: MCP client timeout configuration
The system SHALL pass MCP request timeout from config to HTTP client.

#### Scenario: MCP request with custom timeout
- **WHEN** `TIMEOUT_CONFIG["mcp_request"]` is 15
- **AND** MCPClient makes a request
- **THEN** HTTP request timeout is 15 seconds

#### Scenario: MCP connect timeout
- **WHEN** `TIMEOUT_CONFIG["mcp_connect"]` is 3
- **AND** MCP Service is unreachable
- **THEN** connection attempt fails after 3 seconds

### Requirement: Timeout values are integers in seconds
The system SHALL store all timeout values as integers representing seconds.

#### Scenario: Timeout type validation
- **WHEN** timeout configuration is loaded
- **THEN** all values are integers (not floats or strings)
- **AND** negative values are not allowed
