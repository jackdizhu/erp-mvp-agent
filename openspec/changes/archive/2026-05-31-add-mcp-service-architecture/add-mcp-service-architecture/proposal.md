## Why

当前 ERP Agent 系统通过直接调用 `erp_app/tools.py` 实现功能，缺乏标准化接口和可扩展性。通过引入 MCP (Model Context Protocol) 服务架构，可以实现：
1. 外部系统通过标准化的 MCP 协议调用 ERP 功能
2. 支持多服务动态注册和运行时配置更新
3. 更好的错误处理和超时控制机制

## What Changes

- **新增 MCP Client 模块**：在 `app/clients/` 中实现标准化的 MCP 客户端，支持 HTTP/JSON-RPC 2.0 协议
- **新增 MCP Registry**：实现服务注册表，支持 JSON 配置文件的加载、热更新和按工具名前缀路由
- **新增独立 MCP Service**：创建 `erp_mcp_service/` 项目，提供 FastAPI 实现的 MCP HTTP 服务
- **新增错误处理模型**：定义 MCP 专属错误码和错误类，提升错误可追溯性
- **新增 Agent 集成**：支持 hybrid 模式运行，保留原有适配器同时支持 MCP 调用
- **可选前端错误展示**：增强前端对 MCP 错误的展示能力

## Capabilities

### New Capabilities

- **mcp-client**: MCP 客户端实现，支持 HTTP/JSON-RPC 2.0、API Key 认证和可配置超时
- **mcp-registry**: MCP 服务注册表，支持 JSON 配置、运行时热更新和服务查找
- **mcp-service**: 独立的 MCP HTTP 服务，提供健康检查、工具列表和工具调用接口
- **mcp-error-model**: MCP 专属错误模型，包括超时、连接失败、认证失败等错误码
- **mcp-agent-integration**: Agent 集成层，支持 hybrid 回退模式和错误传播

### Modified Capabilities

- 无（当前仅实现阶段，不涉及需求变更）

## Impact

- **新增目录**：`app/clients/`, `erp_mcp_service/`
- **修改文件**：`app/config.py`, `app/errors.py`, `app/agent.py`, `app/main.py`, `app/llm.py`
- **配置文件**：`app/config_dir/mcp_servers.json`
- **环境变量**：`CLIENT_BACKEND`, `MCP_SERVICE_URL`, `MCP_REQUEST_TIMEOUT`, `MCP_CONNECT_TIMEOUT`