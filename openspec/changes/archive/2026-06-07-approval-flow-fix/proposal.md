## Why

审批功能不生效：用户点击"确认执行"后系统仍提示"请确认"。根因是 `confirm_action` 通过 `client_factory.execute_tool` 路由到 MCP Service 时，MCP Service 对 DANGER 工具再次创建审批（新 action_id），返回 PENDING 而非执行结果，导致 LLM 看到后再次调用工具，形成审批循环。需要在 Agent 侧实现两阶段审批流程：前端先获取 user_op_id，再携带此 ID 调用 confirm，确保已审批的工具直接执行而非重复审批。

## What Changes

- 新增 `approval_store.py` 审批持久化存储模块，替代 `approval_core` 的内存 dict，支持验证、不支持态标记、user_op_id 生成
- 新增 `/api/approval/create` 和 `/api/approval/decide` 两个审批 API 端点，实现前端两阶段确认流程
- 新增 `app/models.py` 审批 API 请求/响应 Pydantic 数据模型
- 修改 `confirm_action`：按路由模式判断（MCP/ERP），MCP 模式调用 `execute_tool_preapproved` 跳过 MCP 内部审批，传入 `user_op_id`
- 修改 `mcp_client.call_tool` 支持 `params` 参数，新增 `execute_tool_preapproved` 方法传递 `_meta.preapproved` 标志
- 修改 `approval_core.confirm` 增加 `user_op_id` 记录
- 新增 `intent_detector.check_approval_status` 函数，检测已有审批结果避免重复审批
- 修改前端 `httpUtils.js` 新增 `approvalCreate`、`approvalDecide`、`chatConfirmWithUserOp` 函数
- 修改前端 `ApprovalCard.jsx` 支持审批不支持态（无操作按钮）、不可撤销警告
- 修改前端 `ChatPage.jsx` 的 `handleConfirm` 改为两阶段流程：先 approvalDecide 获取 user_op_id，再 chatConfirmWithUserOp

## Capabilities

### New Capabilities
- `approval-store`: 审批记录持久化存储模块，支持创建、验证、不支持标记、审批决定（含 user_op_id 生成）、过期清理
- `approval-api`: 审批 REST API 端点（/api/approval/create、/api/approval/decide），含 Pydantic 请求/响应模型

### Modified Capabilities
- `approval-flow`: confirm 方法增加 user_op_id 参数记录；新增 check_approval_status 函数检查审批状态避免重复审批
- `agent-core`: confirm_action 重写为路由模式判断（MCP 走 execute_tool_preapproved，ERP 走 client_factory），传入 user_op_id
- `chat-api`: 新增 /api/approval/create 和 /api/approval/decide 端点；/chat/confirm 支持 user_op_id 参数
- `chat-ui`: ApprovalCard 支持不支持态（隐藏按钮）；handleConfirm 改为两阶段流程（先 decide 获取 user_op_id，再 confirm 执行）
- `mcp-client`: call_tool 支持 params 参数；新增 execute_tool_preapproved 方法传递 _meta.preapproved 标志

## Impact

- **后端新增文件**: `app/models.py`, `app/approval_store.py`
- **后端修改文件**: `app/main.py`（新增端点）, `app/agent.py`（confirm_action 重写）, `app/clients/mcp_client.py`（新增方法+params 支持）, `app/approval_core.py`（confirm 增加 user_op_id）, `app/intent_detector.py`（新增 check_approval_status）
- **前端修改文件**: `frontend/src/httpUtils.js`, `frontend/src/ApprovalCard.jsx`, `frontend/src/ChatPage.jsx`
- **API 变更**: 新增 2 个端点，/chat/confirm 新增可选参数 user_op_id
- **MCP 协议**: call_tool payload 新增可选 `_meta.preapproved` 和 `_meta.user_op_id` 字段，需 MCP Service 侧配合识别
- **向后兼容**: user_op_id 为可选参数，不传时走原有审批流程
