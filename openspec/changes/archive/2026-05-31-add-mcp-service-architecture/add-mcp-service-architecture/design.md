## Context

当前 ERP Agent 系统采用直接调用模式，通过 `erp_app/tools.py` 中的 `execute_tool` 函数直接执行工具。这种架构存在以下问题：

1. **缺乏标准化接口**：外部系统无法通过标准协议调用 ERP 功能
2. **无服务隔离**：工具执行与 Agent 紧耦合，难以独立部署和扩展
3. **错误处理不完善**：缺少针对远程调用的超时、认证、连接失败等错误处理
4. **配置不灵活**：不支持运行时动态添加/移除服务

本变更引入 MCP (Model Context Protocol) 架构，实现服务标准化和可扩展性。

## Goals / Non-Goals

**Goals:**
- 实现 MCP Client 模块，支持 HTTP/JSON-RPC 2.0 协议调用远程 MCP 服务
- 实现 MCP Registry，支持 JSON 配置文件的加载、热更新和按工具名前缀路由
- 创建独立的 `erp_mcp_service` 项目，提供标准的 MCP HTTP 服务接口
- 支持 hybrid 模式运行，同时保留原有 ErpAdapter 作为回退方案
- 定义 MCP 专属错误码，提升错误可追溯性

**Non-Goals:**
- 不修改 `erp_app/tools.py` 的核心逻辑（工具实现保持不变）
- 不实现完整的 MCP 协议规范（仅实现当前业务所需的端点）
- 不强制要求使用 MCP（通过配置控制，可回退到原有架构）

## Decisions

### 1. ClientFactory 模块化架构

**选择**：保持 `ClientFactory` 作为统一入口，集成 ErpAdapter 和 MCPClient

**理由**：
- 最小化对现有代码的影响（Agent 无需感知底层调用方式）
- 支持 hybrid 模式，当 MCP 服务不可用时自动回退到本地适配器
- 通过 `CLIENT_BACKEND` 环境变量控制后端选择

**替代方案考虑**：
- 完全替换 ErpAdapter → 增加回滚风险
- 创建独立的 MCP 路由层 → 增加架构复杂度

### 2. MCP Registry 热更新机制

**选择**：通过 `POST /api/mcp/reload` 端点触发配置重载

**理由**：
- 支持运行时动态更新服务配置，无需重启 Agent
- 配置变更通过 JSON Schema 验证，确保格式正确
- 在进行客户端移除前等待进行中的调用完成

**替代方案考虑**：
- 文件监控自动重载 → 增加复杂度，可能引入竞态条件
- 定时轮询 → 增加资源消耗

### 3. MCP Service 独立部署

**选择**：创建独立的 `erp_mcp_service/` 项目

**理由**：
- 服务职责单一，易于独立部署和扩展
- 允许未来其他系统通过 MCP 协议调用 ERP 功能
- 便于独立测试和监控

**替代方案考虑**：
- 在 Agent 内部实现 MCP 服务 → 违反单一职责原则
- 使用 Docker 容器化 → 增加运维复杂度

### 4. 错误处理模型

**选择**：定义 MCP 专属错误码，映射到标准 AgentError

**理由**：
- MCP 服务可能返回多种错误类型，需要标准化处理
- 便于前端根据错误码展示友好的错误信息
- 支持错误追溯和监控

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| MCP 服务不可用 | Agent 功能降级 | 实现 hybrid 模式，自动回退到 ErpAdapter |
| 网络超时导致响应慢 | 用户体验下降 | 配置合理的超时时间（默认 10s） |
| 配置错误导致服务崩溃 | 系统无法启动 | 实现 graceful fallback，缺失配置时使用默认值 |
| 并发调用竞争条件 | 数据不一致 | Registry 移除客户端前等待进行中的调用完成 |

## Migration Plan

### Phase 1: 灰度验证
1. 保持 `CLIENT_BACKEND=erp_adapter`，仅启用本地适配器
2. 启动 MCP Service，与现有架构并行运行
3. 通过测试脚本验证功能一致性

### Phase 2: 切换配置
1. 确认 MCP Service 延迟差异 < 5%、覆盖率 = 100%、错误率 < 0.1%
2. 修改 `CLIENT_BACKEND=mcp` 或 `CLIENT_BACKEND=hybrid`
3. 监控错误率和延迟指标

### Rollback Procedure
1. 设置 `CLIENT_BACKEND=erp_adapter`
2. 重启 Agent 服务
3. 验证原有接口正常工作
4. 保留 MCP Service 用于后续调试

## Open Questions

1. **API Key 管理**：当前通过配置文件存储 API Key，考虑迁移到环境变量或密钥管理系统
2. **监控指标**：是否需要添加 Prometheus 指标暴露端点？
3. **服务发现**：未来是否需要支持 Consul/Eureka 等服务发现机制？