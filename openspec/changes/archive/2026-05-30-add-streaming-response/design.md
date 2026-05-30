## Context

当前系统 `/chat` 端点为同步阻塞模式，用户发送消息后需等待 LLM 完整响应（通常 5-15 秒）才能看到结果。期间无任何中间状态反馈，工具调用结果以原始 JSON 展示，缺乏可视化处理。

## Goals / Non-Goals

**Goals:**
- 新增 SSE 流式端点 `/chat/stream`，支持分阶段推送 Agent 执行状态
- 前端支持流式消息渲染，实时显示思考和工具执行过程
- 工具调用结果升级为结构化卡片展示
- 保留 `/chat` 端点向后兼容

**Non-Goals:**
- 不修改现有 `/chat` 端点行为
- 不引入 WebSocket（SSE 足够且更简单）
- 不实现多路复用或连接池管理

## Decisions

### Decision 1: 使用 SSE 而非 WebSocket

**选择**: Server-Sent Events (SSE)

**理由**:
- 单向推送（服务端 → 客户端），符合聊天场景
- 浏览器原生支持，无需w额外库
- 自动重连机制内置
- 比 WebSocket 更简单的服务端实现

**替代方案**:
- WebSocket: 双向通信过度设计，增加服务端复杂度
- 长轮询: 效率低，浪费资源

### Decision 2: SSE 事件类型设计

```
事件流:
  event: thinking
  data: {"stage": "analyzing_intent", "message": "正在理解您的意图..."}

  event: tool_call
  data: {"tool": "query_order", "args": {"order_id": "123"}, "status": "executing"}

  event: tool_result
  data: {"tool": "query_order", "result": {...}, "status": "completed"}

  event: reply_chunk
  data: {"content": "订"}

  event: reply_chunk
  data: {"content": "单"}

  event: done
  data: {"complete": true, "tool_calls": [...], "pending_action": null}
```

### Decision 3: 前端流式渲染架构

```
┌─────────────────────────────────────────────────────┐
│  StreamingMessage.jsx                                │
│  ┌───────────────────────────────────────────────┐  │
│  │  ThinkingIndicator  (thinking 事件)            │  │
│  │  ToolStatusCard     (tool_call/result 事件)    │  │
│  │  MessageContent     (reply_chunk 事件累加)     │  │
│  │  FinalActions       (done 事件)                │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  EventSource 管理:                                   │
│  ├── 连接建立 → 创建消息占位                         │
│  ├── 接收事件 → 追加内容到对应组件                    │
│  ├── 连接关闭 → 标记消息完成                         │
│  └── 连接错误 → 降级到同步模式                       │
└─────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| SSE 连接超时 | 设置合理超时时间，前端自动重连 |
| 事件乱序 | 事件设计为幂等，不依赖顺序 |
| 前端渲染性能 | 节流处理 reply_chunk，避免频繁 DOM 更新 |
| 浏览器兼容性 | SSE 在现代浏览器广泛支持，IE11 降级到同步模式 |
