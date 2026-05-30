## Purpose

Delta spec: tool system registration moves from `app/tools.py` to `erp_app/tools.py`. Agent accesses tools via `erp_client` instead of direct import. Tool schemas, registry, and execution remain functionally identical.

## MODIFIED Requirements

### Requirement: Tool registry maps names to implementations
The system SHALL maintain a `TOOL_REGISTRY` dictionary mapping tool name strings to their Python implementation functions in `erp_app/tools.py`, not in `app/tools.py`. The agent SHALL access tool execution via `app/erp_client.execute_tool()` which delegates to `erp_app/tools.execute_tool()`.

#### Scenario: Tool execution via registry
- **WHEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "123"})`
- **THEN** system routes to `erp_app.TOOL_REGISTRY["query_order"](order_id="123")` and returns the result

#### Scenario: Unknown tool returns error
- **WHEN** agent calls `erp_client.execute_tool("nonexistent_tool", {})`
- **THEN** system returns TOOL_NOT_FOUND error

### Requirement: Tool schema definition in OpenAI format
The system SHALL define all tool schemas using OpenAI's function calling format in `erp_app/tools.py`. The agent SHALL obtain schemas via `erp_client.get_tools()` instead of importing `TOOL_SCHEMAS` directly.

#### Scenario: Tool schemas passed to LLM
- **WHEN** agent calls LLM
- **THEN** all 9 tool schemas are obtained via `erp_client.get_tools()` and included in the tools parameter

## REMOVED Requirements

### Requirement: Tool schemas defined in app/tools.py
**Reason**: Moved to `erp_app/tools.py` as part of service split
**Migration**: Use `erp_client.get_tools()` to access schemas

### Requirement: Tool registry defined in app/tools.py
**Reason**: Moved to `erp_app/tools.py` as part of service split
**Migration**: Use `erp_client.execute_tool()` to execute tools
