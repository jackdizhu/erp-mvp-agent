## 1. SSE 流式端点实现

- [x] 1.1 在 `app/main.py` 中新增 POST /chat/stream 端点
- [x] 1.2 实现 SSE 响应格式化器（event/data 格式）
- [x] 1.3 在 `app/agent.py` 中新增 `stream_chat()` 函数，支持事件推送回调
- [x] 1.4 实现 thinking 事件推送（意图识别阶段）
- [x] 1.5 实现 tool_call/tool_result 事件推送（工具执行阶段）
- [x] 1.6 实现 reply_chunk 事件推送（LLM 流式输出）
- [x] 1.7 实现 done 事件推送（完成状态）

## 2. 前端流式渲染组件

- [x] 2.1 创建 `frontend/src/StreamingMessage.jsx` 流式消息组件
- [x] 2.2 创建 `frontend/src/ThinkingIndicator.jsx` 思考状态指示器
- [x] 2.3 创建 `frontend/src/ToolStatusCard.jsx` 工具状态卡片
- [x] 2.4 创建 `frontend/src/DataVizCard.jsx` 数据可视化卡片
- [x] 2.5 实现 EventSource 管理器，处理连接生命周期
- [x] 2.6 在 `ChatPage.jsx` 中集成流式模式，支持同步/流式切换
- [x] 2.7 实现降级逻辑：SSE 失败时回退到 /chat 端点

## 3. UI/UX 增强

- [x] 3.1 新增加载动画和进度指示器
- [x] 3.2 实现工具调用结果的结构化渲染（表格/卡片）
- [x] 3.3 实现消息内容的打字机效果
- [x] 3.4 优化消息气泡样式，区分用户/助手/系统状态
- [x] 3.5 添加快捷指令按钮（常用查询模板）

## 4. 配置与测试

- [x] 4.1 在 `app/config.py` 中新增 SSE 配置项
- [x] 4.2 编写 SSE 端点单元测试
- [x] 4.3 编写前端流式渲染组件测试
- [x] 4.4 集成测试：验证流式响应完整流程
- [x] 4.5 性能测试：对比同步/流式响应延迟

## 5. 文档更新

- [x] 5.1 更新 `README.zh.md` 新增流式响应说明
- [x] 5.2 更新 API 文档，新增 /chat/stream 端点说明
- [x] 5.3 添加前端组件使用指南
