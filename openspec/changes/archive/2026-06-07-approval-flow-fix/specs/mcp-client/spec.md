## ADDED Requirements

### Requirement: Execute tool preapproved
The system SHALL provide execute_tool_preapproved(name, args, user_op_id=None) method on MCPClient that calls call_tool with _meta.preapproved=true and _meta.user_op_id to bypass MCP Service internal approval.

#### Scenario: Execute preapproved MCP tool
- **WHEN** mcp_client.execute_tool_preapproved("mcp_update_order", {"order_id": "123"}, user_op_id="uop_xxxxxxxxxxxx") is called
- **THEN** system calls call_tool with name="mcp_update_order", args={"order_id": "123"}, params={"_meta": {"preapproved": true, "user_op_id": "uop_xxxxxxxxxxxx"}}

#### Scenario: Execute preapproved without user_op_id
- **WHEN** mcp_client.execute_tool_preapproved("mcp_update_order", {"order_id": "123"}) is called
- **THEN** system calls call_tool with params={"_meta": {"preapproved": true, "user_op_id": None}}

## MODIFIED Requirements

### Requirement: MCPClient HTTP implementation
The system SHALL implement an `MCPClient` class in `app/clients/mcp_client.py` that communicates with MCP Services via HTTP POST + JSON-RPC 2.0. The call_tool method SHALL accept an optional `params` dict to merge additional parameters (such as _meta) into the JSON-RPC request.

#### Scenario: Call tool execution
- **WHEN** `mcp_client.call_tool("mcp_query_order", {"order_id": "123"})` is called
- **THEN** the system sends POST to `/mcp/tools/call` with JSON-RPC request
- **AND** returns the tool execution result

#### Scenario: Call tool with extra params
- **WHEN** `mcp_client.call_tool("mcp_update_order", {"order_id": "123"}, params={"_meta": {"preapproved": true}})` is called
- **THEN** the system sends POST to `/mcp/tools/call` with JSON-RPC request where params includes both "name", "arguments", and "_meta" fields

#### Scenario: Handle MCP service unavailable
- **WHEN** MCP Service returns connection error or 503
- **THEN** the system raises MCPServiceUnavailable error with error code MCP_SERVICE_UNAVAILABLE
