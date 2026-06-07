## 1. 审批存储与数据模型

- [x] 1.1 新建 `app/models.py`，定义 ApprovalCreateRequest、ApprovalCreateResponse、ApprovalDecideRequest、ApprovalDecideResponse Pydantic 模型
- [x] 1.2 新建 `app/approval_store.py`，实现 ApprovalRecord 类（含 to_dict）和 ApprovalStore 类（create、validate、mark_unsupported、decide、get、_cleanup_expired）
- [x] 1.3 在 approval_store 中创建全局单例 approval_store 实例

## 2. 审批 API 端点

- [x] 2.1 在 `app/main.py` 中新增 POST /api/approval/create 端点，调用 approval_store.validate 并返回 ApprovalCreateResponse
- [x] 2.2 在 `app/main.py` 中新增 POST /api/approval/decide 端点，调用 approval_store.decide 并返回 ApprovalDecideResponse

## 3. 审批核心逻辑修改

- [x] 3.1 修改 `app/approval_core.py` 的 confirm 方法，增加 user_op_id 可选参数，在返回结果中记录 user_op_id
- [x] 3.2 在 `app/intent_detector.py` 中新增 check_approval_status(action_id) 函数，查询 approval_store 返回审批状态

## 4. Agent 确认执行重写

- [x] 4.1 修改 `app/agent.py` 的 confirm_action 函数，增加 user_op_id 参数，传递给 approval_core.confirm
- [x] 4.2 在 confirm_action 中实现路由模式判断：通过 client_factory._mcp_tool_alias 判断 MCP/ERP 模式
- [x] 4.3 MCP 模式调用 mcp_client.execute_tool_preapproved，ERP 模式调用 client_factory.execute_tool
- [x] 4.4 添加降级逻辑：MCP 客户端不支持 execute_tool_preapproved 时回退到 client_factory.execute_tool

## 5. MCP 客户端修改

- [x] 5.1 修改 `app/clients/mcp_client.py` 的 call_tool 方法，增加可选 params 参数，合并到 JSON-RPC payload
- [x] 5.2 新增 execute_tool_preapproved(name, args, user_op_id) 方法，调用 call_tool 传入 _meta.preapproved 和 _meta.user_op_id

## 6. 前端 HTTP 工具函数

- [x] 6.1 在 `frontend/src/httpUtils.js` 中新增 approvalCreate(actionId, tool, args, sessionId) 函数
- [x] 6.2 新增 approvalDecide(actionId, approved, sessionId) 函数
- [x] 6.3 新增 chatConfirmWithUserOp(sessionId, actionId, approved, history, userOpId) 函数

## 7. 前端审批卡片修改

- [x] 7.1 修改 `frontend/src/ApprovalCard.jsx`，支持 approvalMeta.supported=false 时不渲染操作按钮，显示不支持原因
- [x] 7.2 添加 UNSUPPORTED 状态到状态标签映射

## 8. 前端两阶段审批流程

- [x] 8.1 修改 `frontend/src/ChatPage.jsx` 的 handleConfirm，改为两阶段：先调 approvalDecide 获取 user_op_id，再调 chatConfirmWithUserOp
- [x] 8.2 处理 decide 阶段失败（无 user_op_id）时更新卡片为 failed 状态
- [x] 8.3 处理 confirm 阶段失败时更新卡片为 failed 状态

## 9. 集成验证

- [x] 9.1 验证正常审批流程：用户点击确认 → 两阶段执行 → 不再重复审批
- [x] 9.2 验证审批不支持态：不支持的操作显示灰色卡片，无按钮
- [x] 9.3 验证重复点击防护：actionLoading 阻止重复请求
- [x] 9.4 验证过期审批：后端返回 TOOL_EXPIRED
- [x] 9.5 验证向后兼容：不传 user_op_id 时走原有审批流程
