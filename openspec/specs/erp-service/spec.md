## Purpose

Define the ERP service package structure, tool registration, and business logic layer that replaces the current monolithic app/ package.

## Requirements

### Requirement: ERP service package structure
The system SHALL organize the ERP service as a separate Python package `erp_app/` containing tool registration, business logic services, data layer, configuration, and error definitions.

#### Scenario: Package initialization
- **WHEN** the application starts
- **THEN** `erp_app/__init__.py` exports the main API router for mounting

#### Scenario: Directory structure
- **WHEN** erp_app package is examined
- **THEN** it contains: `tools.py`, `main.py`, `db.py`, `models.py`, `seed.py`, `config.py`, `errors.py`, `approval_detail.py`, `services/order_service.py`, `services/inventory_service.py`, `services/supplier_service.py`

### Requirement: Tool schemas defined in erp_app
The system SHALL define all tool schemas (`TOOL_SCHEMAS`) in `erp_app/tools.py` using OpenAI's function calling format, replacing the current definition in `app/tools.py`.

#### Scenario: Tool schemas accessible via erp_app
- **WHEN** erp_app is imported
- **THEN** `TOOL_SCHEMAS` contains all 9 tool definitions (query_order, query_orders, query_inventory, query_supplier, create_order, update_order, cancel_order, delete_order, adjust_inventory)

### Requirement: Tool registry in erp_app
The system SHALL maintain `TOOL_REGISTRY` in `erp_app/tools.py` mapping tool names to their implementation functions from the service layer.

#### Scenario: Tool execution via erp_app registry
- **WHEN** `execute_tool("query_order", {"order_id": "123"})` is called on erp_app
- **THEN** the system routes to order_service.query_order and returns the result

#### Scenario: Unknown tool returns error
- **WHEN** `execute_tool("nonexistent_tool", {})` is called
- **THEN** the system raises TOOL_NOT_FOUND error

### Requirement: ERP internal API router
The erp_app package SHALL define a FastAPI APIRouter with endpoints for tool execution and approval detail generation, mountable at `/erp` prefix on the main application.

#### Scenario: Router mountable at /erp
- **WHEN** erp_app.main.router is mounted on the main FastAPI app
- **THEN** routes are accessible at `/erp/tools/schemas`, `/erp/tools/execute`, `/erp/approval/detail`

### Requirement: MCP unified endpoint at /mcp and /
The MCP Service (`erp_mcp_service/`) SHALL expose a unified MCP endpoint at `/mcp` and `/` that dispatches JSON-RPC requests by `method` field.

#### Scenario: MCP unified endpoint at /mcp
- **WHEN** MCP Service receives `POST /mcp` with `method: "tools/list"`
- **THEN** the system dispatches to the tools list handler and returns JSON-RPC response

#### Scenario: MCP unified endpoint at /
- **WHEN** MCP Service receives `POST /` with `method: "initialize"`
- **THEN** the system dispatches to the initialize handler and returns JSON-RPC response

### Requirement: Risk level and limits configuration in erp_app
The system SHALL define `TOOL_RISK_LEVELS`, `TOOL_LIMITS`, and `ACTION_SUMMARIES` in `erp_app/config.py`, removing them from `app/config.py`.

#### Scenario: Risk level lookup
- **WHEN** erp_app config is accessed for "update_order"
- **THEN** the system returns "DANGER"

#### Scenario: Tool limits configuration
- **WHEN** erp_app config is accessed for "create_order"
- **THEN** the system returns max_items=5 (configurable via TOOL_LIMIT_CREATE env var)
