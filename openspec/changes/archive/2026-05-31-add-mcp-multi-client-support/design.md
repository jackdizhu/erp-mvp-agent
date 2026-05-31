## Context

当前 MCP 服务（`erp_mcp_service`）已实现 Streamable HTTP 传输和 Session 管理，但存在多客户端并发连接问题：

- ERP Agent 客户端使用 `f"init_{id(self)}"` 生成请求 ID（Python 对象地址格式）
- Trae IDE 等外部客户端使用 UUID 格式
- 服务端 Session 未按客户端隔离，并发请求可能导致 ID 冲突
- 缺少客户端标识机制，无法区分请求来源

现有组件：
- `SessionManager`：已有 session 创建/过期/清理，但无 pending_requests 追踪
- `MCPClient`：请求 ID 非标准，无客户端标识 header
- 服务端 `_dispatch_method`：直接处理请求，无请求追踪

## Goals / Non-Goals

**Goals:**
- 支持多个 MCP 客户端同时连接同一服务端
- 统一 JSON-RPC 请求 ID 为 UUID v4 格式
- 通过 X-Client-Id header 区分客户端来源
- 服务端按 session 追踪 pending requests

**Non-Goals:**
- 不实现客户端认证/授权（已有 API Key 机制）
- 不实现请求限流/配额
- 不修改 Trae IDE 内置 MCP 客户端行为
- 不实现 WebSocket 传输

## Decisions

### D1: 请求 ID 使用 UUID v4

**选择**: 客户端每次请求生成 `str(uuid.uuid4())`

**替代方案**:
- 递增计数器：简单但多客户端易冲突
- 对象地址：当前方案，不可预测且非标准

**理由**: UUID v4 是 JSON-RPC 实践中最通用的 ID 格式，与 Trae 等外部客户端兼容

### D2: X-Client-Id Header 标识客户端

**选择**: 客户端在请求头中携带 `X-Client-Id: <uuid>`，服务端按此隔离请求

**替代方案**:
- 仅依赖 session_id：session 在 initialize 后才创建，首次请求无法区分
- User-Agent：语义不符，格式不统一

**理由**: 显式客户端标识，在 initialize 阶段即可区分来源，与现有 session 机制互补

### D3: Session 增加 pending_requests 追踪

**选择**: 在 Session 数据类中增加 `pending_requests: Dict[str, float]`，记录 request_id → timestamp

**替代方案**:
- 全局请求追踪：跨 session 查找效率低
- Redis 外部存储：过度设计，单进程场景不需要

**理由**: 最小改动，利用现有 SessionManager 基础设施，自动随 session 过期清理

### D4: 服务端严格回显 request id

**选择**: 服务端响应中 `id` 字段必须等于请求中的 `id`

**当前状态**: `_build_response` 已正确回显，但 `_dispatch_method` 中部分路径可能丢失 id

**理由**: JSON-RPC 2.0 规范要求，确保客户端能匹配请求与响应

## Risks / Trade-offs

- [Risk] 旧版客户端未发送 X-Client-Id → 服务端为无标识客户端分配默认 client_id，保持向后兼容
- [Risk] pending_requests 内存泄漏 → 设置 TTL（60s），随 session cleanup 自动清理
- [Risk] UUID 碰撞概率极低但非零 → 可接受，UUID v4 碰撞概率约 10^-18