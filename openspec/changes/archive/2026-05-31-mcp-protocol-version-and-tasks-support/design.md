## Context

MCP Service 当前使用协议版本 `2025-03-26`，导致新版 IDE (如 TRAE) 无法连接，因为它们使用 `2025-11-25` 协议。同时，ERP 批量操作（如 `query_orders`）耗时较长，需要 MCP Tasks 功能支持异步追踪和进度反馈。

当前架构：
- `erp_mcp_service/main.py` - MCP 服务端，使用 `PROTOCOL_VERSION = "2025-03-26"`
- `app/clients/mcp_client.py` - 内部 MCP 客户端，使用相同版本
- `erp_mcp_service/tools.py` - 工具定义，无 taskSupport 声明

## Goals / Non-Goals

**Goals:**
- 升级 MCP 协议版本到 `2025-11-25`，让新版 IDE 能正常连接
- 实现 MCP Tasks 功能，支持长时间运行的批量操作异步追踪
- 声明工具级别的 `taskSupport`，让客户端知道哪些工具支持任务增强

**Non-Goals:**
- 不需要支持多版本共存（旧版客户端同步升级）
- 不需要实现进度推送（SSE/WebSocket），仅支持轮询模式
- 不需要 OAuth 认证（当前通过 X-API-Key header 认证）

## Decisions

### 1. 协议版本升级方式

**选择**: 直接升级到 `2025-11-25`，服务端和客户端同步更新

**理由**:
- 用户明确不需要多版本共存
- `mcp_client.py` 是内部客户端，可以同步升级
- 简化版本检查逻辑，无需维护版本列表

### 2. Tasks 实现模式

**选择**: 请求方驱动 + 轮询模式

```
Client ──▶ tools/call (带 task:{ttl:60000}) ──▶ Server
                    (立即返回 taskId)
Client ◀─── {taskId, status: "working"} ◀─── Server

Client ──▶ tasks/status?taskId=xxx ──▶ Server (轮询)
Client ◀─── {status, progress?} ◀─── Server

Client ──▶ tasks/complete?taskId=xxx ──▶ Server
Client ◀─── {result, status: "completed"} ◀─── Server
```

**理由**:
- HTTP 传输层已支持，无需额外 WebSocket/SSE
- 实现简单，符合 MCP Tasks 规范的基本要求
- 足够满足 ERP 批量操作场景

### 3. 任务状态存储

**选择**: 内存存储（Dict）+ TTL 过期机制

```python
_tasks: Dict[str, TaskState] = {}

class TaskState:
    task_id: str
    status: str  # pending/working/completed/failed/canceled
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[dict] = None
    created_at: float
    ttl: int  # 毫秒
```

**理由**:
- 当前是单实例服务，无需分布式存储
- TTL 机制自动清理过期任务
- 实现简单，满足需求

**替代方案**:
- Redis 存储（未来需要多实例部署时迁移）
- 数据库存储（过度设计）

### 4. 工具 Task 支持策略

| 工具 | taskSupport | 理由 |
|------|-------------|------|
| `query_orders` | `optional` | 批量查询，耗时长 |
| `query_order` | `forbidden` | 单个订单，快速 |
| `create_order` | `forbidden` | 单个操作，快速 |
| `update_order_status` | `forbidden` | 单个操作，快速 |
| `list_suppliers` | `optional` | 数据量大时耗时 |
| `search_suppliers` | `optional` | 数据量大时耗时 |

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 协议版本升级后旧版客户端不兼容 | 内部 mcp_client.py 无法使用 | 同步升级 mcp_client.py 版本 |
| 任务状态丢失（服务重启） | 进行中的任务状态丢失 | 提示用户重试 |
| TTL 设置不合理 | 任务未完成就被清理 | 默认 60 秒，可按需调整 |
| 长时间任务占用内存 | 大量任务堆积 | 任务完成/失败后立即清理 |

## Open Questions

1. **Tasks TTL 默认值**: 建议 60 秒还是 120 秒？
2. **批量查询的大小限制**: 是否需要限制单次查询的最大订单数？
3. **任务列表上限**: 是否需要限制 `tasks/list` 返回的任务数量？