## Context

MCP Service 当前 `POST /mcp` 只返回 `Content-Type: application/json`，但 MCP 2025-11-25 Streamable HTTP 规范要求服务端根据客户端 Accept header 选择响应格式。IDE (TRAE) 发送 `Accept: application/json, text/event-stream`，期望 SSE 格式响应。

当前架构：
- `erp_mcp_service/main.py` - 单一 `POST /mcp` 端点，只返回 JSON
- 无 `GET /mcp` 端点（SSE 长连接）
- 无会话管理

## Goals / Non-Goals

**Goals:**
- POST /mcp 支持 SSE 格式响应（当客户端 Accept 包含 text/event-stream）
- GET /mcp 支持 SSE 长连接（服务端推送通知）
- Mcp-Session-Id 会话管理
- DELETE /mcp 会话终止
- 完全符合 MCP 2025-11-25 Streamable HTTP 规范

**Non-Goals:**
- 不需要支持旧版 HTTP+SSE 传输（2024-11-05）
- 不需要支持 SSE 重连/重发（Last-Event-ID）
- 不需要支持批量 JSON-RPC 消息

## Decisions

### 1. SSE 响应格式选择

**选择**: POST /mcp 始终返回 SSE 格式（当 Accept 包含 text/event-stream）

```
Content-Type: text/event-stream

event: message
data: {"jsonrpc":"2.0","id":"xxx","result":{...}}

```

**理由**:
- IDE 期望 SSE 格式
- SSE 格式兼容 JSON 客户端（数据仍是 JSON）
- 符合规范要求

### 2. 会话管理方式

**选择**: 内存存储 + UUID Session ID

```python
class Session:
    session_id: str
    created_at: float
    last_activity: float
    sse_connections: List  # 活跃的 SSE 连接
    message_queue: Queue   # 待推送的消息队列
```

**理由**:
- 单实例服务，无需分布式存储
- UUID 足够安全
- 内存存储性能最优

### 3. GET /mcp 推送机制

**选择**: 异步 Queue + SSE 流

```
GET /mcp (Accept: text/event-stream)
    ↓
服务端创建 SSE 流
    ↓
Queue 中有消息时推送
    ↓
无消息时发送 keep-alive ping (每 30 秒)
```

**理由**:
- Queue 天然支持异步推送
- keep-alive 防止代理/防火墙超时
- 符合规范要求

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| SSE 长连接占用内存 | 大量并发连接时内存增长 | 设置连接超时和最大连接数 |
| 服务重启丢失会话 | 客户端需要重新初始化 | 可接受，MCP 协议支持重连 |
| 防火墙/代理中断 SSE | 连接被中间层关闭 | keep-alive ping 防超时 |

## Open Questions

1. **SSE 连接超时**: 默认 300 秒还是更长？
2. **最大并发 SSE 连接数**: 默认 100 是否足够？