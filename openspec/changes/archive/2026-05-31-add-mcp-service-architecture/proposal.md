## Why

当前 ERP Agent 通过内部模块 `erp_app` 直接调用业务逻辑，虽已通过 `ErpClient` 实现了接口解耦，但随着业务扩展：
1. 多业务域（HR、CRM、供应链）需要统一工具调用协议
2. LLM 调用超时（默认配置）导致工具执行不完整
3. MCP 服务不可用时缺乏明确的前端提示
4. 服务间缺少标准认证机制

MCP (Model Context Protocol) 提供了标准化的工具调用协议，可实现跨服务、跨领域的统一扩展能力。

## What Changes

1. **MCP Client 架构**
   - 创建 `app/clients/` 模块，实现通用 MCP Client
   - 通过 HTTP 协议调用独立 MCP Service
   - 支持工具注册和动态发现

2. **MCP Registry 配置驱动**
   - 通过 `app/config_dir/mcp_servers.json` 声明式注册 MCP 服务
   - JSON 格式兼容 Trae/Claude MCP 生态（`mcpServers` 结构）
   - 启动时自动加载，支持运行时热加载（`POST /api/mcp/reload`）
   - 支持多服务注册、按名称/工具前缀查找

2. **MCP Service (ERP)**
   - 将 `erp_app` 改造为独立 MCP Service
   - 实现 MCP Protocol Server (tools/list, tools/call)
   - 暴露标准 HTTP API 端点

3. **超时可配置**
   - LLM 调用超时支持配置文件设置（默认 15s）
   - MCP 服务调用超时可配置

4. **错误处理增强**
   - MCP 服务不可用时返回标准错误到前端
   - 统一错误码增加 MCP 相关错误类型

5. **API Key 认证**
   - MCP Service 实现 API Key 认证
   - Agent 端配置密钥存储

6. **CLIENT_BACKEND 环境变量控制**
   - `hybrid`（默认）：MCP 优先 + 本地回退，渐进迁移
   - `erp_adapter`：使用本地 erp_app，安全回退
   - `mcp`：使用 MCP 服务，无本地回退

## Capabilities

### New Capabilities

- `mcp-client`: Agent 端 MCP Client 实现，支持 HTTP 调用、工具发现、认证
- `mcp-registry`: MCP 服务注册中心，JSON 配置驱动，支持启动加载和运行时热加载
- `mcp-service-erp`: ERP MCP Service，实现标准 MCP Protocol 接口
- `llm-timeout-config`: LLM 调用超时可配置，默认 15s
- `mcp-error-handling`: MCP 服务错误处理，返回统一格式错误

### Modified Capabilities

- `erp-client`: 从内部模块调用改为 MCP Client 调用（实现方式变更，不影响接口）
- `error-handling`: 增加 MCP_SERVICE_UNAVAILABLE 错误码

## Impact

- **代码变更**: `app/clients/` (新增), `app/erp_client.py` (适配), `erp_app/` (改造), `app/config_dir/mcp_servers.json` (新增)
- **配置变更**: `app/config.py` 增加超时配置、MCP 端点配置、CLIENT_BACKEND 环境变量；`mcp_servers.json` 替代硬编码服务注册
- **API 变更**: 新增 `/mcp/*` HTTP 端点，新增 `POST /api/mcp/reload` 热加载端点
- **依赖**: 需安装 MCP Protocol 相关库
- **部署**: 需要同时部署 Agent 和 MCP Service
