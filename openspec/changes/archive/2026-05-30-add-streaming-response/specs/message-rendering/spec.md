## ADDED Requirements

### Requirement: 流式消息渲染组件
前端 SHALL 提供 StreamingMessage 组件，支持接收和渲染 SSE 事件流。

#### Scenario: 流式消息占位创建
- **WHEN** 用户发送消息并建立 SSE 连接
- **THEN** 前端创建消息占位，显示加载指示器

#### Scenario: 内容累加渲染
- **WHEN** 接收到 reply_chunk 事件
- **THEN** 前端将内容累加到消息组件，实时显示

#### Scenario: 消息完成标记
- **WHEN** 接收到 done 事件
- **THEN** 前端标记消息为完成，移除加载指示器

### Requirement: 思考和工具状态指示器
前端 SHALL 提供 ThinkingIndicator 和 ToolStatusCard 组件，显示 Agent 执行状态。

#### Scenario: 思考阶段显示提示
- **WHEN** 接收到 thinking 事件
- **THEN** 前端显示"正在理解您的意图..."等阶段提示

#### Scenario: 工具执行状态显示
- **WHEN** 接收到 tool_call 事件
- **THEN** 前端显示工具名称和参数，标记为"执行中"

#### Scenario: 工具结果状态更新
- **WHEN** 接收到 tool_result 事件
- **THEN** 前端更新工具状态为"已完成"，显示结果摘要

### Requirement: 降级到同步模式
前端 SHALL 在 SSE 不可用时自动降级到同步 /chat 端点。

#### Scenario: SSE 不支持时降级
- **WHEN** 浏览器不支持 EventSource
- **THEN** 前端使用同步 /chat 端点发送请求

#### Scenario: SSE 连接失败时降级
- **WHEN** SSE 连接建立失败或中断
- **THEN** 前端显示错误提示，提供重试按钮
