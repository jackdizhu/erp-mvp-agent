## MODIFIED Requirements

### Requirement: ERP internal API router
The erp_app package SHALL define a FastAPI APIRouter with endpoints for tool execution and approval detail generation, mountable at `/erp` prefix on the main application. The MCP Service (`erp_mcp_service/`) SHALL additionally expose a unified MCP endpoint at `/mcp` and `/` that dispatches JSON-RPC requests by `method` field.

#### Scenario: Router mountable at /erp
- **WHEN** erp_app.main.router is mounted on the main FastAPI app
- **THEN** routes are accessible at `/erp/tools/schemas`, `/erp/tools/execute`, `/erp/approval/detail`

#### Scenario: MCP unified endpoint at /mcp
- **WHEN** MCP Service receives `POST /mcp` with `method: "tools/list"`
- **THEN** the system dispatches to the tools list handler and returns JSON-RPC response

#### Scenario: MCP unified endpoint at /
- **WHEN** MCP Service receives `POST /` with `method: "initialize"`
- **THEN** the system dispatches to the initialize handler and returns JSON-RPC response

### Requirement: Tool schemas defined in erp_app
The system SHALL define all tool schemas (`TOOL_SCHEMAS`) in `erp_app/tools.py` using OpenAI's function calling format. The MCP Service SHALL return these schemas in the MCP `tools/list` response format with `name`, `description`, and `inputSchema` fields.

#### Scenario: Tool schemas accessible via MCP tools/list
- **WHEN** client sends `method: "tools/list"` to the MCP endpoint
- **THEN** the response includes all tool definitions with `name`, `description`, and `inputSchema` fields
