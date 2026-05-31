## Context

当前流式聊天功能在连接失败时，前端仅显示"流式连接失败，请重试"，缺乏具体的错误状态码和上下文信息。这导致：
- 用户无法区分网络错误、服务端错误、超时等不同情况
- 开发者难以通过前端表现快速定位后端问题
- 运维人员无法从日志中追踪完整的错误链路

## Goals / Non-Goals

**Goals:**
- 前端显示详细错误信息（HTTP 状态码、状态文本、错误原因）
- 后端记录流式接口错误日志，包含请求上下文
- MCP 客户端记录 HTTP 请求的详细状态码和响应内容
- 不改变现有功能逻辑，仅增强错误信息传递

**Non-Goals:**
- 不修改 SSE 事件协议格式
- 不引入新的错误重试机制
- 不改变现有的错误恢复流程

## Decisions

### 1. 前端错误对象扩展
**Decision**: 在 `chatStreamReader` 中捕获 HTTP 响应失败时的完整错误信息，构造包含 `status`、`statusText`、`message` 字段的错误对象传递给 `onError` 回调。

**Rationale**: 保持与现有回调接口的兼容性，仅扩展错误对象内容。

**Alternatives considered**:
- 新增 `onHttpError` 回调：增加接口复杂度，不推荐
- 全局错误处理：丢失上下文信息

### 2. 前端错误提示格式
**Decision**: 在 `ChatPage.jsx` 的 `onError` 回调中，根据错误对象构造用户友好的提示消息，格式为：`[状态码] 错误原因`。

**Rationale**: 用户可直接看到问题类型（如 404 表示接口不存在，500 表示服务端错误，0 表示网络不通）。

### 3. 后端错误日志增强
**Decision**: 在 `stream_endpoint` 的异常处理中添加 `logging.error` 记录完整异常堆栈，包含 session_id 等上下文。

**Rationale**: 便于后端日志分析和问题追踪。

### 4. MCP 客户端状态码日志
**Decision**: 在 `_request` 方法中，对非 2xx/3xx 状态码记录详细的 URL、状态码、响应内容。

**Rationale**: MCP 服务连接问题是流式失败的常见原因，需要独立的可观测性。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 错误信息暴露内部实现细节 | 前端仅展示状态码和简要原因，不展示堆栈 |
| 错误消息过长影响 UI | 限制错误提示长度，过长时截断 |
| 后端日志量增加 | 仅记录错误级别日志，不影响正常请求 |

## Migration Plan

1. 部署后端变更（main.py、mcp_client.py）- 无影响，仅增加日志
2. 部署前端变更（httpUtils.js、useStreamingChat.js、ChatPage.jsx）- 用户立即看到更详细的错误提示
3. 观察日志和前端表现，验证错误信息传递链路

**Rollback**: 回滚前端代码即可恢复原有行为

## Open Questions

- 是否需要针对特定状态码提供用户友好的提示模板？（如 404 提示"服务未启动"，500 提示"服务器内部错误"）
