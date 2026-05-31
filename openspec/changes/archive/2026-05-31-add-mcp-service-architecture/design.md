## Context

当前架构采用单体服务 + 内部模块模式，`ErpClient` 作为 thin adapter 连接 Agent 与 ERP 业务逻辑。随着多业务域扩展需求，需要将 ERP 功能独立为 MCP Service，实现服务解耦和标准化扩展。

### 当前架构

```
Agent (app/agent.py)
    │
    └── ErpClient (app/erp_client.py)
            │
            └── erp_app/tools.py (直接 import)
```

### 目标架构

```
Agent (app/agent.py)
    │
    └── MCPClient (app/clients/mcp_client.py) ──── HTTP ──── erp-mcp-service
                                                          │
                                                          └── erp_app/tools.py
```

## Goals / Non-Goals

**Goals:**
- 实现 MCP Protocol 标准接口（tools/list, tools/call）
- LLM 调用超时可通过配置设置（默认 15s）
- MCP 服务不可用时返回明确错误信息到前端
- 实现 API Key 认证机制

**Non-Goals:**
- 不实现 MCP 完整协议（resources、prompts 暂不需要）
- 不改变现有工具的接口和行为
- 不实现多租户隔离（MCP 服务的运行时隔离）

## Decisions

### D1: 传输协议选择 HTTP + JSON-RPC 2.0

**Decision**: 使用 HTTP POST + JSON-RPC 2.0 over HTTP

**Rationale**:
- 已有 FastAPI 基础设施，易于集成
- 相比 stdio，HTTP 支持更好的监控和负载均衡
- JSON-RPC 2.0 是广泛支持的标准

**Alternatives Considered**:
- stdio: 适合本地进程通信，但无法支持分布式部署
- WebSocket: 适合双向实时通信，当前场景不需要

### D2: 工具命名空间带前缀

**Decision**: 工具名格式 `erp_<tool_name>`（如 `erp_query_order`）

**Rationale**:
- 避免多 MCP Service 工具名冲突
- 便于 ClientFactory 路由分发

### D3: MCP Service 复用 erp_app 核心逻辑

**Decision**: MCP Service 作为 thin wrapper，核心逻辑复用 `erp_app/tools.py`

**Rationale**:
- 最小化改造范围
- 保证业务逻辑一致性
- 便于渐进式迁移

### D4: 超时配置结构

**Decision**: 在 `app/config.py` 中定义超时配置结构

```python
TIMEOUT_CONFIG = {
    "llm_call": 15,      # LLM 调用超时（秒）
    "mcp_request": 10,   # MCP 服务请求超时（秒）
    "mcp_connect": 5,    # MCP 服务连接超时（秒）
}
```

### D5: API Key 认证

**Decision**: MCP Service 使用 API Key 认证，Agent 配置中存储密钥

**Rationale**:
- 实现简单，适合内部服务间认证
- 可通过环境变量或配置文件注入密钥
- 不引入复杂的 OAuth 流程

### D6: MCP Service Configuration via JSON

**Decision**: Use `mcp_servers.json` in `app/config_dir/` as the single source of truth for MCP service registration, replacing hardcoded `MCP_SERVICE_CONFIG` dict.

**Rationale**:
- JSON format is compatible with Trae/Claude MCP ecosystem (`mcpServers` structure)
- Declarative configuration is easier to edit and version control
- Supports runtime hot-reload without code changes

**Configuration Schema**:
```json
{
  "mcpServers": {
    "<service_name>": {
      "type": "streamableHttp",
      "url": "<endpoint_url>",
      "headers": { "<key>": "<value>" },
      "timeout": <seconds>
    }
  }
}
```

**Field Definitions**:
- `type`: Transport protocol, currently only `streamableHttp` supported, reserved for future `stdio`/`sse`
- `url`: MCP Service HTTP endpoint
- `headers`: Custom HTTP headers (e.g., `X-API-Key` for authentication)
- `timeout`: Request timeout in seconds (overrides `TIMEOUT_CONFIG.mcp_request`)

**Alternatives Considered**:
- Hardcoded dict in `config.py`: Not flexible, requires code change for each new service
- Environment variables: Difficult to represent nested structure for multiple services

### D7: Runtime Hot-Reload via API

**Decision**: Provide `POST /api/mcp/reload` endpoint to trigger configuration hot-reload without Agent restart.

**Rationale**:
- Production environments require zero-downtime service updates
- Adding/removing MCP services should not interrupt ongoing conversations
- Reload is explicit (API call) rather than implicit (file watcher), avoiding race conditions

**Reload Flow**:
```
1. POST /api/mcp/reload
2. Registry re-reads mcp_servers.json
3. Diff new config vs current config
4. Added services → create MCPClient, register tools
5. Removed services → remove client, unregister tools
6. Updated services → rebuild client with new config
7. Return summary: {"added": N, "removed": N, "updated": N}
```

**Safety Guarantees**:
- In-flight tool calls complete before client removal
- Failed client creation does not affect existing services
- Reload is atomic: all changes applied or none

### D8: MCP Registry Pattern

**Decision**: Implement `MCPRegistry` in `app/clients/mcp_registry.py` as the central manager for MCP client lifecycle.

**Rationale**:
- Single point of management for all MCP clients
- Decouples configuration loading from client creation
- Enables ClientFactory to query registered services dynamically

**Responsibilities**:
- Parse `mcp_servers.json` and validate schema
- Create/destroy MCPClient instances based on config
- Provide service lookup by name or tool prefix
- Track client health status

### D9: CLIENT_BACKEND Environment Variable for Fallback Control

**Decision**: Add `CLIENT_BACKEND` environment variable to control whether Agent uses MCP services or local `erp_app` fallback.

**Rationale**:
- Zero-risk migration: default to `erp_adapter` (local), switch to `mcp` when ready
- Single env var toggle, no code changes needed for rollback
- Supports gradual rollout: dev → staging → production

**Configuration**:
```python
CLIENT_BACKEND = os.getenv("CLIENT_BACKEND", "hybrid")
# Values:
#   "erp_adapter"  - Use local erp_app directly (safe fallback)
#   "mcp"          - Use MCP services via ClientFactory + MCPRegistry
#   "hybrid"       - Use MCP services with erp_adapter as fallback (default)
```

**Behavior by Mode**:

| Mode | Tool Source | Fallback | Use Case |
|------|------------|----------|----------|
| `erp_adapter` | ErpAdapter only | None | Current behavior, safe default |
| `mcp` | MCPRegistry only | None | Full MCP deployment, no fallback |
| `hybrid` | MCPRegistry first | ErpAdapter | Gradual migration, best resilience |

**Startup Flow**:
```
1. Always register ErpAdapter as "erp_local" in ClientFactory
2. If CLIENT_BACKEND in ["mcp", "hybrid"]:
     → MCPRegistry.initialize() → load mcp_servers.json
3. If CLIENT_BACKEND == "erp_adapter":
     → Skip MCPRegistry, use ErpAdapter only
4. If CLIENT_BACKEND == "hybrid":
     → MCP tools take priority, ErpAdapter as fallback for unregistered tools
```

### D10: Agent Integration via ClientFactory

**Decision**: `app/agent.py` replaces direct `erp_client` import with ClientFactory module-level functions.

**Rationale**:
- ClientFactory provides unified tool dispatch regardless of backend mode
- Agent code does not need to know about MCP vs local implementation
- ErpAdapter preserves identical behavior to current `erp_client`

**Changes**:
- `from app.erp_client import erp_client` → `from app.clients import client_factory`
- `erp_client.get_tools()` → `client_factory.get_all_tools()`
- `erp_client.get_risk_level(name)` → `client_factory.get_risk_level(name)`
- `erp_client.execute_tool(name, args)` → `client_factory.execute_tool(name, args)`
- `erp_client.get_approval_detail(name, args)` → `client_factory.get_approval_detail(name, args)`

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 网络延迟导致 LLM 超时 | 工具调用不完整 | 配置合理超时值，增加重试机制 |
| MCP Service 单点故障 | Agent 无法执行工具 | 保留本地 fallback，本地 erp_app 作为降级 |
| API Key 安全泄露 | 服务被未授权调用 | 使用环境变量存储，定期轮换 |
| 迁移期间功能回退 | 用户体验下降 | 并行运行验证，灰度切换 |

## Migration Plan

### Phase 1: 接口抽象（不改变现有行为）
1. 创建 `app/clients/base.py` 定义抽象接口
2. 创建 `app/clients/erp_adapter.py` 保留当前实现
3. 修改 `app/agent.py` 通过接口调用

### Phase 2: MCP Service 实现
1. 创建 `erp-mcp-service/` 项目结构
2. 实现 MCP HTTP Server
3. 实现 tools/list 和 tools/call 端点
4. 添加 API Key 中间件

### Phase 3: MCP Client 实现
1. 实现 `app/clients/mcp_client.py`
2. 实现 `app/clients/client_factory.py`
3. 修改配置支持 MCP 端点

### Phase 4: 切换验证
1. 并行运行新旧服务
2. 功能一致性测试
3. 性能对比验证
4. 切换为 MCP 调用

### Rollback
- Phase 1-2 可随时回退（未改变调用逻辑）
- Phase 3-4 切换 `erp_adapter.py` 实现即可回退

## Open Questions (已解决)

### Q1: MCP Service 是否需要健康检查端点？
**决策**：实现 GET `/health` 端点

**结论**：
- 端点：`GET /health`
- 响应：`{"status": "healthy", "service": "erp-mcp-service"}`
- 用途：负载均衡器探测、服务监控、Agent 降级判断
- 优先级：Phase 2 实现

### Q2: 是否需要实现工具变更的 webhook 通知？
**决策**：Phase 1-2 暂不实现，后续按需添加

**结论**：
- 理由：工具变更频率低，可通过 Agent 重启刷新
- 备选方案：Agent 实现定时轮询 `/mcp/tools/list` 检测变更
- 触发条件：当工具动态注册成为核心需求时再实现

### Q3: 多 MCP Service 场景下，ClientFactory 的工具聚合策略？
**决策**：工具命名空间前缀路由 + 优先级权重

**结论**：
- 路由规则：工具名匹配 `erp_*` → ERP MCP Service，`crm_*` → CRM MCP Service
- 聚合逻辑：ClientFactory 调用所有 Service 的 `list_tools()`，合并去重后返回
- 冲突处理：同名工具保留优先级高的 Service 版本
- 配置示例：
  ```python
  MCP_SERVICE_CONFIG = {
      "erp": {"endpoint": "http://localhost:8001", "priority": 1},
      "crm": {"endpoint": "http://localhost:8002", "priority": 2},
  }
  ```
