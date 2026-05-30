## Why

当前系统所有 LLM 调用为同步阻塞模式，用户发送消息后需等待 5-15 秒才能看到完整回复，期间无任何状态反馈。工具调用结果以原始 JSON 展示，缺乏可视化处理。这种体验会导致用户焦虑和信任度下降，尤其对非技术用户不友好。

## What Changes

- 后端新增 SSE (Server-Sent Events) 流式端点 `/chat/stream`
- Agent 循环拆分为多阶段推送：意图识别 → 工具调用 → 结果生成
- 前端支持流式消息渲染，实时显示思考过程和工具执行状态
- 工具调用结果从 JSON 原始展示升级为结构化卡片（表格/状态标签）
- 新增加载动画和进度指示器
- 保留原有 `/chat` 端点向后兼容

## Capabilities

### New Capabilities
- `streaming-api`: SSE 流式响应端点，支持分阶段推送 Agent 执行状态
- `message-rendering`: 流式消息渲染组件，支持打字机效果和状态指示
- `data-visualization`: 工具调用结果的结构化展示（表格/图表/时间线）

### Modified Capabilities
- `chat-api`: `/chat` 端点保持不变，新增 `/chat/stream` 可选端点
- `chat-ui`: 消息渲染逻辑升级，支持流式内容追加和状态组件
- `agent-core`: Agent 循环增加状态推送回调接口
- `tool-system`: 工具执行增加进度事件推送能力

## Impact

- **后端 API**: 新增 `/chat/stream` SSE 端点；Agent 循环增加 `on_event` 回调
- **前端组件**: `ChatPage.jsx` 新增流式消息处理器；新增 `StreamingMessage.jsx`、`ToolStatusCard.jsx`、`DataVizCard.jsx`
- **通信协议**: 引入 SSE `text/event-stream`，事件类型：`thinking`、`tool_call`、`tool_result`、`reply_chunk`、`done`
- **兼容性**: 原有 `/chat` 端点完全保留，前端可配置选择同步/流式模式
- **性能**: SSE 连接保持活跃，需考虑连接池和超时处理
