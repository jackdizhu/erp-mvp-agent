## Purpose

Define the thin adapter layer that enables the agent core to communicate with the ERP service through a clean interface, decoupling agent logic from ERP implementation details.

## ADDED Requirements

### Requirement: ErpClient provides tool schema retrieval
The system SHALL implement an `ErpClient` class in `app/erp_client.py` with a `get_tools()` method that returns the `TOOL_SCHEMAS` list from `erp_app/tools.py` for passing to the LLM.

#### Scenario: Get tool schemas
- **WHEN** agent calls `erp_client.get_tools()`
- **THEN** it returns the full list of 9 tool schemas from erp_app

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
