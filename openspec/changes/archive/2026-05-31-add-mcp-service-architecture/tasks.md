## 1. Config & Error Model

- [x] 1.1 Add `TIMEOUT_CONFIG` to `app/config.py` with llm_call=15, mcp_request=10, mcp_connect=5
- [x] 1.2 Add MCP-specific error codes to `app/errors.py`: MCP_SERVICE_UNAVAILABLE, MCP_CONNECTION_TIMEOUT, MCP_INVALID_RESPONSE, MCP_TOOL_NOT_FOUND, MCP_AUTH_FAILED
- [x] 1.3 Update `AgentError` class to support MCP error sources

## 2. MCP Client Implementation

- [x] 2.1 Create `app/clients/` directory structure with `__init__.py`
- [x] 2.2 Create `app/clients/base.py` with abstract `BaseClient` interface
- [x] 2.3 Create `app/clients/mcp_client.py` implementing MCPClient with HTTP/JSON-RPC 2.0
- [x] 2.4 Implement API Key authentication in MCPClient (read from headers in config)
- [x] 2.5 Implement configurable timeout in MCPClient
- [x] 2.6 Create `app/clients/client_factory.py` for multi-service support
- [x] 2.7 Create `app/clients/erp_adapter.py` preserving current ErpClient behavior

## 2.5. MCP Registry Implementation

- [x] 2.5.1 Create `app/clients/mcp_registry.py` with MCPRegistry class
- [x] 2.5.2 Implement JSON schema validation for `mcp_servers.json`
- [x] 2.5.3 Implement startup loading: parse JSON → create MCPClient instances
- [x] 2.5.4 Implement graceful fallback when config file missing or invalid
- [x] 2.5.5 Implement service lookup by name (`get_client(name)`)
- [x] 2.5.6 Implement service lookup by tool prefix (`get_client_for_tool(tool_name)`)
- [x] 2.5.7 Implement runtime hot-reload: diff config, add/remove/update clients
- [x] 2.5.8 Ensure in-flight calls complete before client removal
- [x] 2.5.9 Add `POST /api/mcp/reload` endpoint in `app/main.py`
- [x] 2.5.10 Create default `app/config_dir/mcp_servers.json` template with erp service entry

## 3. MCP Service ERP Implementation

- [x] 3.1 Create `erp_mcp_service/` project structure
- [x] 3.2 Implement MCP HTTP Server with FastAPI
- [x] 3.3 Implement GET `/health` health check endpoint
- [x] 3.4 Implement POST `/mcp/tools/list` endpoint returning JSON-RPC 2.0 response
- [x] 3.5 Implement POST `/mcp/tools/call` endpoint with tool execution
- [x] 3.6 Add API Key authentication middleware
- [x] 3.7 Delegate tool execution to `erp_app/tools.py` functions
- [x] 3.8 Add JSON-RPC 2.0 error response handling

## 3.5. MCP Service Bug Fixes

- [x] 3.5.1 Fix `erp_mcp_service/tools.py` sys.path import order (import sys before sys.path.insert)
- [x] 3.5.2 Fix `erp_mcp_service/config.py` missing `from pathlib import Path`
- [x] 3.5.3 Fix `erp_mcp_service/main.py` add DB init and seed on startup

## 4. Agent Integration

- [x] 4.1 Add `CLIENT_BACKEND` to `app/config.py` with env var control (erp_adapter/mcp/hybrid)
- [x] 4.2 Update `app/clients/client_factory.py` to use ErpAdapter instead of erp_client, support hybrid fallback
- [x] 4.3 Update `app/agent.py` to use ClientFactory module-level functions instead of erp_client
- [x] 4.4 Update `app/main.py` startup: register ErpAdapter → init MCPRegistry based on CLIENT_BACKEND
- [x] 4.5 Update `app/llm.py` to use configurable LLM timeout
- [x] 4.6 Add MCP error handling in `stream_chat()` and `chat()` functions
- [x] 4.7 Ensure error responses include MCP errors for frontend display

## 5. Frontend Error Display

- [ ] 5.1 Update frontend to display MCP_SERVICE_UNAVAILABLE errors
- [ ] 5.2 Add error notification component for MCP service errors
- [ ] 5.3 Test error display in streaming and non-streaming modes

## 6. Testing & Migration

- [ ] 6.1 Create unit tests for MCPClient
- [ ] 6.2 Create unit tests for MCP Service endpoints
- [ ] 6.3 Create integration tests for MCP communication
- [ ] 6.4 Verify parallel running with current architecture

### 6.5 Parallel Run Verification

- [ ] 6.5.1 Define test criteria: latency diff < 5%, coverage = 100%, error rate < 0.1%
- [ ] 6.5.2 Start current architecture (ErpClient direct call to erp_app)
- [ ] 6.5.3 Start MCP Service and configure ClientFactory to point to new endpoint
- [ ] 6.5.4 Execute functional comparison test script
- [ ] 6.5.5 Record latency and error rate
- [ ] 6.5.6 Switch configuration after verification passes

### 6.6 Rollback Procedure

- [ ] 6.6.1 Define trigger conditions: coverage < 99%, error rate > 1%, latency diff > 10%
- [ ] 6.6.2 Set `CLIENT_BACKEND=erp_adapter` in environment to switch back
- [ ] 6.6.3 Restart Agent service
- [ ] 6.6.4 Verify old interface works correctly
- [ ] 6.6.5 Keep MCP Service for subsequent debugging