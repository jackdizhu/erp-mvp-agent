## Purpose

Define the frontend chat interface including layout, message rendering, approval cards, session sidebar, and input area behavior.

## Requirements

### Requirement: Chat page layout
The system SHALL render a single ChatPage with a collapsible session sidebar on the left and a chat area on the right, using React + Vite + native CSS.

#### Scenario: Page loads with sidebar and chat area
- **WHEN** user opens the application
- **THEN** chat page renders with sidebar showing session list and chat area showing active session messages

### Requirement: Message rendering
The system SHALL render user messages and agent replies in the chat area, with distinct visual styling for each role. Agent messages SHALL display tool_calls and pending_actions when present.

#### Scenario: User message displayed
- **WHEN** a message with role="user" exists in the session
- **THEN** it renders with user styling (right-aligned or distinct color)

#### Scenario: Agent reply with tool calls displayed
- **WHEN** an agent message contains tool_calls
- **THEN** tool call details (tool name, args, result summary) are rendered below the reply text

### Requirement: Approval card component
The system SHALL render an ApprovalCard component for each pending_action in an agent message, displaying action_type, fields, risk_level, and confirm/cancel buttons. Each card operates independently.

#### Scenario: Single approval card rendered
- **WHEN** agent message contains one pending_action
- **THEN** one approval card renders with operation details and confirm/cancel buttons

#### Scenario: Multiple approval cards rendered independently
- **WHEN** agent message contains two pending_actions
- **THEN** two separate approval cards render, each with its own confirm/cancel buttons

#### Scenario: Confirm button triggers /chat/confirm
- **WHEN** user clicks confirm on an approval card
- **THEN** POST /chat/confirm is called with the card's action_id and approved=true

#### Scenario: Cancel button triggers /chat/confirm
- **WHEN** user clicks cancel on an approval card
- **THEN** POST /chat/confirm is called with the card's action_id and approved=false

### Requirement: Approval card unsupported state
The system SHALL render the ApprovalCard in an unsupported state when approvalMeta.supported is false, hiding confirm/cancel buttons and displaying the reason.

#### Scenario: Unsupported approval card
- **WHEN** ApprovalCard receives approvalMeta with supported=false and reason="ORDER_NOT_FOUND"
- **THEN** card displays "不支持: ORDER_NOT_FOUND" status, no confirm/cancel buttons are rendered

#### Scenario: Supported approval card with buttons
- **WHEN** ApprovalCard receives approvalMeta with supported=true
- **THEN** card displays confirm and cancel buttons as normal

### Requirement: Two-stage approval confirmation flow
The system SHALL implement a two-stage handleConfirm flow: first call approvalDecide to obtain user_op_id, then call chatConfirmWithUserOp with the user_op_id to execute the tool.

#### Scenario: Successful two-stage confirmation
- **WHEN** user clicks confirm on an approval card
- **THEN** system calls approvalDecide(actionId, true, sessionId), receives user_op_id, then calls chatConfirmWithUserOp(sessionId, actionId, true, history, user_op_id)

#### Scenario: Successful two-stage rejection
- **WHEN** user clicks cancel on an approval card
- **THEN** system calls approvalDecide(actionId, false, sessionId), receives user_op_id, then calls chatConfirmWithUserOp(sessionId, actionId, false, history, user_op_id)

#### Scenario: Decide API failure
- **WHEN** approvalDecide returns an error (no user_op_id)
- **THEN** system updates approval card state to "failed" and displays error

#### Scenario: Confirm API failure after decide
- **WHEN** chatConfirmWithUserOp returns an error
- **THEN** system updates approval card state to "failed"

### Requirement: Approval HTTP utility functions
The system SHALL provide approvalCreate, approvalDecide, and chatConfirmWithUserOp functions in httpUtils.js.

#### Scenario: approvalCreate API call
- **WHEN** approvalCreate("act_abc123", "update_order", {order_id: "123"}, "sess_1") is called
- **THEN** sends POST to /api/approval/create with body {action_id: "act_abc123", tool: "update_order", args: {order_id: "123"}, session_id: "sess_1"}

#### Scenario: approvalDecide API call
- **WHEN** approvalDecide("act_abc123", true, "sess_1") is called
- **THEN** sends POST to /api/approval/decide with body {action_id: "act_abc123", approved: true, session_id: "sess_1"}

#### Scenario: chatConfirmWithUserOp API call
- **WHEN** chatConfirmWithUserOp("sess_1", "act_abc123", true, history, "uop_xxxxxxxxxxxx") is called
- **THEN** sends POST to /chat/confirm with body {session_id: "sess_1", action_id: "act_abc123", approved: true, history, user_op_id: "uop_xxxxxxxxxxxx"}

### Requirement: Approval card state transitions
The system SHALL visually update approval cards through states: PENDING (red border, buttons visible), CONFIRMED/EXECUTING (yellow, "执行中..."), SUCCESS (green, result shown), FAILED (red, error shown), REJECTED (gray, "已取消"), EXPIRED (gray, "已过期"), UNSUPPORTED (gray, "不支持" reason shown, no buttons).

#### Scenario: Card transitions from pending to success
- **WHEN** user confirms a card and execution succeeds
- **THEN** card border turns green, buttons disappear, result is displayed

#### Scenario: Card transitions from pending to rejected
- **WHEN** user cancels a card
- **THEN** card border turns gray, buttons disappear, "已取消" is displayed

#### Scenario: Card shows expired state
- **WHEN** a pending card's TTL has expired
- **THEN** card border turns gray, buttons are disabled, "已过期" is displayed

#### Scenario: Card shows unsupported state
- **WHEN** approvalMeta.supported is false
- **THEN** card border turns gray, no buttons displayed, "不支持: {reason}" is shown

### Requirement: Input area with send button
The system SHALL render an input area with a text input and send button. During pending approval state, the input area SHALL be disabled.

#### Scenario: Send message
- **WHEN** user types a message and clicks send or presses Enter
- **THEN** message is sent via POST /chat and added to the session

#### Scenario: Input disabled during approval
- **WHEN** there are pending approval cards in PENDING state
- **THEN** input area is disabled with a hint "请先处理待确认操作"

#### Scenario: Input re-enabled after all approvals resolved
- **WHEN** all pending approval cards are in a final state (SUCCESS/FAILED/REJECTED/EXPIRED)
- **THEN** input area is re-enabled

### Requirement: Session sidebar
The system SHALL render a collapsible sidebar showing session list with titles and timestamps, a "新建会话" button, and allow switching/deleting sessions.

#### Scenario: Sidebar shows sessions
- **WHEN** page loads with existing sessions
- **THEN** sidebar lists all sessions with title and creation time, active session highlighted

#### Scenario: Create new session
- **WHEN** user clicks "新建会话"
- **THEN** a new empty session is created and becomes active

#### Scenario: Delete session
- **WHEN** user clicks delete on a session
- **THEN** session is removed from list and localStorage

### Requirement: DANGER operation irreversible warning
The system SHALL display a "此操作不可撤销" warning on approval cards for irreversible operations (delete_order).

#### Scenario: Delete order shows irreversible warning
- **WHEN** approval card for delete_order is rendered
- **THEN** card displays "⚠️ 此操作不可撤销" warning text

### Requirement: 流式消息渲染组件
The system SHALL provide a StreamingMessage component that receives and renders SSE event streams.

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
The system SHALL provide ThinkingIndicator and ToolStatusCard components to display Agent execution state.

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
The system SHALL automatically fall back to the synchronous /chat endpoint when SSE is unavailable.

#### Scenario: SSE 不支持时降级
- **WHEN** 浏览器不支持 EventSource
- **THEN** 前端使用同步 /chat 端点发送请求

#### Scenario: SSE 连接失败时降级
- **WHEN** SSE 连接建立失败或中断
- **THEN** 前端显示错误提示，提供重试按钮

### Requirement: 工具结果结构化展示
The system SHALL provide a DataVizCard component to render tool call results as structured visualizations instead of raw JSON.

#### Scenario: 订单数据表格展示
- **WHEN** query_order 返回订单数据
- **THEN** 前端渲染为表格格式，包含订单 ID、状态、商品、金额等字段

#### Scenario: 库存数据卡片展示
- **WHEN** query_inventory 返回库存数据
- **THEN** 前端渲染为库存状态卡片，包含数量、预留、可用量可视化

#### Scenario: 批量查询结果列表展示
- **WHEN** query_orders 返回多个订单数据
- **THEN** 前端渲染为列表格式，每条订单一行摘要
