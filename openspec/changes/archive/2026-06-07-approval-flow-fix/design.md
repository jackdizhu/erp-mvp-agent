## Context

当前审批流程存在循环问题：Agent 检测到 DANGER 工具后创建审批（action_id），前端展示审批卡片，用户点击"确认执行"后调用 `/chat/confirm`，`confirm_action` 通过 `client_factory.execute_tool` 路由到 MCP Service，MCP Service 再次对 DANGER 工具创建新审批（新 action_id），返回 PENDING 状态。LLM 收到 PENDING 后再次尝试调用工具，形成无限循环。

当前架构约束：
- Agent 通过 `client_factory.execute_tool` 统一路由，不区分 MCP/ERP 模式
- MCP Service 对 DANGER 工具有独立的审批机制，与 Agent 侧审批互不感知
- 前端 `/chat/confirm` 只传 `action_id` 和 `approved`，无用户操作凭证

## Goals / Non-Goals

**Goals:**
- 修复审批循环：用户确认后工具直接执行，不再重复审批
- 实现两阶段审批：前端先获取 user_op_id（用户操作凭证），再携带此 ID 执行
- 支持审批不支持态：后端验证不通过时前端隐藏操作按钮
- 保持向后兼容：user_op_id 为可选参数，不传时走原有流程

**Non-Goals:**
- 不重构 MCP Service 侧审批机制（仅通过 preapproved 标志绕过）
- 不实现审批持久化到 Redis/DB（MVP 阶段保持内存存储）
- 不实现审批权限控制（如角色审批）
- 不修改流式审批流程（本次仅修复非流式模式）

## Decisions

### Decision 1: 新建 approval_store.py 替代 approval_core 内存 dict

**选择**: 新建独立 `ApprovalStore` 类，结构化管理审批记录生命周期

**备选方案**:
- A) 直接修改 `approval_core.py` 的 pending_actions dict → 耦合度高，approval_core 承担过多职责
- B) 新建 approval_store.py 作为独立模块 → 职责分离，便于后续扩展 Redis/DB

**理由**: approval_core 负责审批创建/确认逻辑，approval_store 负责数据持久化和验证，职责清晰。当前 MVP 用内存存储，但接口预留持久化扩展。

### Decision 2: 两阶段审批流程（decide → confirm）

**选择**: 前端先调 `/api/approval/decide` 获取 user_op_id，再调 `/chat/confirm` 携带 user_op_id 执行

**备选方案**:
- A) 单阶段：/chat/confirm 内部生成 user_op_id → 无法区分"用户确认"和"LLM 自动重试"
- B) 两阶段：decide 生成凭证，confirm 消费凭证 → 明确区分用户意图和自动行为

**理由**: user_op_id 作为用户操作的不可伪造凭证，MCP Service 可据此跳过内部审批。两阶段流程使审批状态变更可追溯。

### Decision 3: MCP 模式通过 _meta.preapproved 标志绕过内部审批

**选择**: `execute_tool_preapproved` 在 call_tool 的 params 中注入 `_meta.preapproved=true` 和 `_meta.user_op_id`

**备选方案**:
- A) 修改 MCP Service 添加新端点 → 改动大，需同步修改 MCP Service
- B) 通过 _meta 字段传递标志 → MCP 协议标准字段，MCP Service 只需识别即可

**理由**: MCP 协议的 `_meta` 字段用于传递元信息，不改变工具调用语义。MCP Service 侧仅需检查 `_meta.preapproved` 即可跳过审批，改动最小。

### Decision 4: confirm_action 按路由模式判断执行方式

**选择**: 通过 `client_factory._mcp_tool_alias` 判断工具属于 MCP 还是 ERP，MCP 走 `execute_tool_preapproved`，ERP 走 `client_factory.execute_tool`

**备选方案**:
- A) 统一走 client_factory.execute_tool 加 params → client_factory 需感知审批状态，耦合
- B) 按路由模式分别处理 → 逻辑清晰，各路径独立

**理由**: MCP 和 ERP 的审批机制不同，分开处理避免逻辑混杂。ERP 模式无二次审批问题，保持原有执行路径。

### Decision 5: 审批不支持态通过后端返回 supported=false 实现

**选择**: `/api/approval/create` 验证审批可行性，不支持时返回 `supported=false` + reason

**理由**: 前端无法判断审批是否可执行（如订单已删除、状态已变更），需后端验证。不支持时前端隐藏按钮，避免用户操作无效审批。

## Risks / Trade-offs

- **[MCP Service 未识别 preapproved]** → MCP Service 需配合实现 `_meta.preapproved` 检查，否则仍会二次审批。**缓解**: 先在 Agent 侧实现，MCP Service 侧为后续迭代；降级时走原有流程。
- **[approval_store 内存存储丢失]** → 服务重启后审批记录丢失。**缓解**: MVP 阶段可接受，审批 TTL 仅 300 秒；后续扩展 Redis/DB。
- **[两阶段增加前端复杂度]** → handleConfirm 需串行调用两个 API。**缓解**: 封装为 `chatConfirmWithUserOp` 统一处理，错误时显示 failed 状态。
- **[_mcp_tool_alias 内部属性依赖]** → confirm_action 依赖 client_factory 内部属性判断路由。**缓解**: 后续可提取为 client_factory 的公共方法 `is_mcp_tool(name)`。
