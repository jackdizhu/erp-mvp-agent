## Purpose

Define the thin adapter layer that enables the agent core to communicate with the ERP service through a clean interface, decoupling agent logic from ERP implementation details.

## Requirements

### Requirement: ErpClient provides tool schema retrieval
The system SHALL implement an `ErpClient` class in `app/erp_client.py` with a `get_tools()` method that returns the `TOOL_SCHEMAS` list from `erp_app/tools.py` for passing to the LLM.

#### Scenario: Get tool schemas
- **WHEN** agent calls `erp_client.get_tools()`
- **THEN** it returns the full list of 9 tool schemas from erp_app

### Requirement: MCPClient connects via unified endpoint
The system SHALL implement an `MCPClient` class in `app/clients/mcp_client.py` that sends all JSON-RPC requests to the MCP service's unified endpoint (`/mcp`). The client SHALL perform an `initialize` handshake before the first tool operation.

#### Scenario: Client initializes connection
- **WHEN** `MCPClient` is created and first tool operation is called
- **THEN** the client sends `POST /mcp` with `method: "initialize"` containing `protocolVersion`, `capabilities`, and `clientInfo`
- **AND** the client receives the server's `protocolVersion`, `capabilities`, and `serverInfo`
- **AND** the client sends `POST /mcp` with `method: "notifications/initialized"`

#### Scenario: Get tool schemas via unified endpoint
- **WHEN** agent calls `mcp_client.get_tools()` after successful initialization
- **THEN** the client sends `POST /mcp` with `method: "tools/list"` and returns the full list of tool schemas

### Requirement: MCPClient initialize handshake
The system SHALL implement a complete initialize handshake process per MCP specification. The client SHALL send the initialize request with protocol version and client capabilities, then send the notifications/initialized notification after receiving the server response.

#### Scenario: Initialize with full client capabilities
- **WHEN** client performs initialize handshake
- **THEN** the request includes:
  ```
  {
    "jsonrpc": "2.0",
    "id": "...",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {
        "roots": {"listChanged": true},
        "sampling": {}
      },
      "clientInfo": {
        "name": "erp-agent",
        "version": "1.0.0"
      }
    }
  }
  ```

#### Scenario: Initialize response handling
- **WHEN** client receives initialize response from server
- **THEN** the client extracts `protocolVersion`, `capabilities`, `serverInfo`, and `instructions` from the result
- **AND** the client sends the `notifications/initialized` notification

#### Scenario: Initialize with version mismatch
- **WHEN** client receives initialize error with unsupported protocol version
- **THEN** the client SHOULD disconnect and raise an appropriate error

### Requirement: MCPClient lazy initialization
The system SHALL implement lazy initialization for the MCP handshake. The handshake SHALL only occur on the first tool operation (either `list_tools()` or `call_tool()`), not during client construction. The client SHALL cache the initialization state to avoid repeated handshakes.

#### Scenario: First tool call triggers initialization
- **WHEN** agent calls `mcp_client.execute_tool("query_order", {...})` for the first time
- **THEN** the client performs initialize handshake before executing the tool

#### Scenario: Subsequent tool calls skip initialization
- **WHEN** agent calls `mcp_client.execute_tool("query_order", {...})` after successful initialization
- **THEN** the client directly sends the `tools/call` request without repeating handshake

#### Scenario: Client tracks initialization state
- **WHEN** `MCPClient._initialized` flag is `True`
- **THEN** all subsequent tool calls skip the initialization sequence

### Requirement: MCPClient provides tool execution
The system SHALL implement an `execute_tool(name, args)` method on `MCPClient` that sends a `tools/call` JSON-RPC request to the MCP service's unified endpoint (`/mcp`) and returns the result dict.

#### Scenario: Execute a SAFE tool via unified endpoint
- **WHEN** agent calls `mcp_client.execute_tool("query_order", {"order_id": "123"})`
- **THEN** the client sends `POST /mcp` with:
  ```
  {
    "jsonrpc": "2.0",
    "id": "...",
    "method": "tools/call",
    "params": {
      "name": "query_order",
      "arguments": {"order_id": "123"}
    }
  }
  ```
- **AND** returns the order data from the JSON-RPC result

#### Scenario: Execute a tool that raises error via unified endpoint
- **WHEN** agent calls `mcp_client.execute_tool("query_order", {"order_id": "999"})` for a non-existent order
- **THEN** the JSON-RPC error response is converted to a ValueError for agent error handling

### Requirement: MCPClient timeout handling
The system SHALL enforce configurable timeouts for all MCP requests to prevent hung connections. The client SHALL raise an appropriate error when a request exceeds the timeout.

#### Scenario: Request times out
- **WHEN** MCP request does not receive a response within the configured timeout
- **THEN** the client raises a timeout error

### Requirement: MCPClient health check
The system SHALL implement a `health_check()` method that sends a GET request to `/health` endpoint to verify the MCP service is running.

#### Scenario: Service is healthy
- **WHEN** client calls `health_check()`
- **THEN** the client sends GET to `http://{endpoint}/health` and returns `True` if status is 200

#### Scenario: Service is unavailable
- **WHEN** client calls `health_check()` and the service is not responding
- **THEN** the client returns `False`

### Requirement: ErpClient provides tool execution
The system SHALL implement an `execute_tool(name, args)` method on `ErpClient` that delegates to `erp_app/tools.py`'s `execute_tool()` function and returns the result dict.

#### Scenario: Execute a SAFE tool
- **WHEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "123"})`
- **THEN** the system routes to erp_app and returns the order data

#### Scenario: Execute a CAUTION tool
- **WHEN** agent calls `erp_client.execute_tool("create_order", {"type": "sales", "items": [{"sku": "iPhone-15", "qty": 2}], "customer": "张三"})`
- **THEN** the system executes via erp_app, reserves inventory, and returns the new order

#### Scenario: Execute a tool that raises error
- **WHEN** agent calls `erp_client.execute_tool("query_order", {"order_id": "999"})` for a non-existent order
- **THEN** the ValueError propagates to the agent for error handling

### Requirement: ErpClient provides approval detail retrieval
The system SHALL implement a `get_approval_detail(tool_name, args)` method on `ErpClient` that calls `erp_app/approval_detail.py` to generate approval detail with fields comparing old vs new values.

#### Scenario: Get approval detail for update_order
- **WHEN** agent calls `erp_client.get_approval_detail("update_order", {"order_id": "123", "field": "address", "value": "北京"})`
- **THEN** the system queries SQLite for the current order, and returns fields containing original address, new address, and order status

#### Scenario: Get approval detail for delete_order
- **WHEN** agent calls `erp_client.get_approval_detail("delete_order", {"order_id": "125"})`
- **THEN** the system returns fields with order details and sets irreversible=true

### Requirement: ErpClient error handling
The system SHALL catch and re-raise ERP-specific errors as standardized AgentError types that the agent core can handle, maintaining error compatibility with the existing error model.

#### Scenario: DATA_NOT_FOUND error propagated
- **WHEN** erp_app raises DATA_NOT_FOUND for a missing order
- **THEN** ErpClient passes through the same error for agent error handling

#### Scenario: SYS_ERROR on unexpected failure
- **WHEN** erp_app encounters an unexpected database error
- **THEN** ErpClient wraps it as a SYS_ERROR for agent handling

### Requirement: ErpClient is stateless singleton
The system SHALL implement ErpClient as a stateless singleton that does not maintain any execution state between calls, ensuring thread safety for concurrent requests.

#### Scenario: Concurrent tool executions
- **WHEN** two concurrent requests execute different tools through ErpClient
- **THEN** both complete successfully without interfering with each other
