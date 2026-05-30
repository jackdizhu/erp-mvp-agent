## Purpose

Define the SSE streaming API endpoint and event types for real-time agent response delivery.

## Requirements

### Requirement: SSE 流式响应端点
系统 SHALL 提供 POST /chat/stream 端点，返回 text/event-stream 格式的流式响应。

#### Scenario: 流式端点返回 SSE 格式
- **WHEN** 客户端发送 POST /chat/stream 请求
- **THEN** 系统返回 Content-Type: text/event-stream 的流式响应

#### Scenario: 流式端点支持相同消息格式
- **WHEN** 客户端发送与 /chat 相同的请求格式
- **THEN** 系统返回相同内容，但分阶段推送

### Requirement: SSE 事件类型
系统 SHALL 支持以下 SSE 事件类型：thinking、tool_call、tool_result、reply_chunk、done。

#### Scenario: thinking 事件推送
- **WHEN** Agent 开始处理请求
- **THEN** 系统推送 thinking 事件，包含阶段标识和提示消息

#### Scenario: tool_call 事件推送
- **WHEN** Agent 决定调用工具
- **THEN** 系统推送 tool_call 事件，包含工具名称和参数

#### Scenario: tool_result 事件推送
- **WHEN** 工具执行完成
- **THEN** 系统推送 tool_result 事件，包含工具结果

#### Scenario: reply_chunk 事件推送
- **WHEN** LLM 生成回复内容
- **THEN** 系统逐个推送 reply_chunk 事件，包含内容片段

#### Scenario: done 事件推送
- **WHEN** Agent 完成所有处理
- **THEN** 系统推送 done 事件，包含完整的 tool_calls 和 pending_action

### Requirement: 流式前端渲染
前端 SHALL 支持流式消息渲染，实时显示 Agent 执行状态和内容。

#### Scenario: 流式消息组件接收事件
- **WHEN** 前端接收到 SSE 事件
- **THEN** 对应组件实时更新显示状态

#### Scenario: 连接错误降级处理
- **WHEN** SSE 连接失败
- **THEN** 前端自动降级到同步 /chat 端点

### Requirement: 工具结果可视化
前端 SHALL 将工具调用结果从原始 JSON 升级为结构化卡片展示。

#### Scenario: 订单查询结果表格展示
- **WHEN** query_order 返回订单数据
- **THEN** 前端渲染为表格格式，展示订单详情

#### Scenario: 库存查询结果卡片展示
- **WHEN** query_inventory 返回库存数据
- **THEN** 前端渲染为库存状态卡片，包含数量、预留、可用量
