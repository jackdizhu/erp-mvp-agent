## Why

当前 MCP Service 实现采用 REST 风格多路由设计（`/mcp/tools/list`、`/mcp/tools/call`），不符合 MCP Streamable HTTP 规范（2025-03-26）要求的单一端点 + `method` 分发模式。Trae IDE 的 MCP 客户端遵循规范 POST 到根路径 `/`，导致 404 错误，ERP MCP 服务完全无法被 IDE 发现和连接。同时，MCP Service 端口 8001 被其他 Node.js 服务占用，且端口和 URL 配置硬编码在 JSON 文件中，无法通过环境变量灵活调整。

## What Changes

1. **MCP Streamable HTTP 合规**
   - 新增单一端点 `/mcp`，按 JSON-RPC `method` 字段分发请求
   - 同时支持 `/` 路径，兼容 IDE 默认配置
   - 实现 `initialize` 握手方法（MCP 协议必需）
   - 实现 `notifications/initialized` 通知处理（返回 202 Accepted）
   - 支持 `MCP-Protocol-Version` 响应头
   - 检查客户端 `Accept` 头包含 `application/json` 和 `text/event-stream`
   - **BREAKING**: 旧路由 `/mcp/tools/list`、`/mcp/tools/call` 标记为 deprecated，保留兼容但推荐迁移

2. **MCP 端口可配置**
   - MCP Service 默认端口从 8001 改为 9001，避免与现有服务冲突
   - 端口通过 `MCP_SERVICE_PORT` 环境变量可配置（已部分实现）

3. **MCP Service URL 环境变量覆盖**
   - 新增 `MCP_SERVICE_URL` 环境变量，覆盖 `mcp_servers.json` 中的 URL 配置
   - `mcp_registry.py` 启动时优先读取环境变量，未设置时回退到 JSON 配置
   - `mcp_servers.json` 默认 URL 更新为 `http://localhost:9001/mcp`

4. **MCP Client 适配**
   - `mcp_client.py` 改造为使用单一端点 `/mcp` 发送请求
   - 新增 `initialize` 握手流程：连接时先发送 `initialize`，再发送 `notifications/initialized`
   - 保留 `health_check()` 使用 `/health` 端点

## Capabilities

### New Capabilities

- `mcp-streamable-http`: MCP Streamable HTTP 传输层实现，包含单一端点、initialize 握手、method 分发、协议版本协商
- `mcp-config-env`: MCP 服务配置环境变量覆盖机制，支持 MCP_SERVICE_URL 和 MCP_SERVICE_PORT 环境变量

### Modified Capabilities

- `erp-client`: MCPClient 从多路由调用改为单一端点调用，新增 initialize 握手流程
- `erp-service`: MCP Service 端点结构从 REST 多路由改为 Streamable HTTP 单一端点，新增 initialize 方法处理

## Impact

- **代码变更**: `erp_mcp_service/main.py`（重写端点路由）、`app/clients/mcp_client.py`（适配单一端点 + 握手）、`app/clients/mcp_registry.py`（环境变量覆盖）、`app/config.py`（新增 MCP_SERVICE_URL）
- **配置变更**: `erp_mcp_service/config.py`（端口 9001）、`app/config_dir/mcp_servers.json`（URL 更新为 `http://localhost:9001/mcp`）
- **API 变更**: 新增 `POST /mcp` 和 `POST /` 端点；旧端点 `/mcp/tools/list`、`/mcp/tools/call` 保留但 deprecated
- **部署变更**: MCP Service 端口从 8001 变更为 9001，需更新 Trae IDE MCP 配置中的 URL
- **向后兼容**: 旧路由继续工作，内部客户端可渐进迁移
