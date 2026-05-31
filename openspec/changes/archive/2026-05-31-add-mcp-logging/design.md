## Context

当前 MCP Client (`app/clients/mcp_client.py`) 和 MCP Service (`erp_mcp_service/main.py`) 日志不完整。现有日志仅包含初始化握手的部分信息（`performing initialize handshake`、`initialize successful`），但 `_request()` 方法只有错误日志，`list_tools()` 和 `call_tool()` 完全没有日志。这导致调试 issue-012 至 issue-015 时只能依赖猜测。

MCP 调用链路：
```
Agent → MCPClient._request() → MCP Service /mcp → _dispatch_method() → tool execution
```

## Goals / Non-Goals

**Goals:**
- 在 MCP Client 的 `_request()` 中记录每次 HTTP 请求的完整信息（method、URL、请求体、响应、duration）
- 在 `list_tools()` 和 `call_tool()` 中记录调用结果（tools 数量、result/error 摘要）
- 在 MCP Service 的端点和 `_dispatch_method()` 中记录每次请求的完整信息
- 统一日志格式，便于日志聚合和分析

**Non-Goals:**
- 不处理数据脱敏（params 和 result 完整记录）
- 不改变接口行为，仅增加日志输出
- 不实现日志轮转或持久化（由部署环境处理）

## Decisions

### D1: 日志格式 — 结构化 JSON 日志

**选择**: 使用 Python `logging` 模块输出 JSON 格式日志，包含 timestamp、method、params、result/error、duration

**备选方案**:
- A: 纯文本日志 — 简单但难以解析
- B: JSON 结构化日志 — 可被日志聚合工具（如 ELK、Loki）解析
- C: 打印到 stdout — 调试方便但不规范

**理由**: JSON 格式日志便于日志聚合和分析工具处理，同时可以通过 `json.dumps()` 保持可读性。

### D2: 日志级别 — INFO

**选择**: MCP 调用日志使用 `logging.INFO` 级别

**理由**:
- `DEBUG` 级别可能产生过多噪音
- `ERROR` 级别仅记录错误，不记录正常调用
- `INFO` 级别平衡了详细程度和可读性

### D3: 日志字段 — 完整记录

每条 MCP 调用日志包含：
```python
{
    "timestamp": "2026-05-31T15:00:00.123456",
    "level": "INFO",
    "logger": "mcp_client" | "mcp_service",
    "method": "tools/call",
    "params": {...},
    "result": {...} | "error": {...},
    "duration_ms": 45
}
```

### D4: 日志位置 — 客户端 + 服务端

**选择**: 在 MCP Client 和 MCP Service 都添加日志

**备选方案**:
- A: 仅客户端记录 — 服务端无日志
- B: 仅服务端记录 — 客户端无日志
- C: 两者都记录 — 完整链路追踪

**理由**: 完整链路追踪需要两端日志，便于定位问题在客户端还是服务端。

## Risks / Trade-offs

- **[日志量增加]** → INFO 级别日志会产生较多输出，可通过日志级别过滤控制
- **[敏感信息暴露]** → 不做脱敏处理，需确保日志访问权限受控