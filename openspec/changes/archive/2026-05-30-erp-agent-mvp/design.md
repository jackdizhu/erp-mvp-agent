## Context

项目从零构建 ERP Agent MVP，当前仅有设计文档（docs/erp-mvp-agent.md），无任何代码。核心验证目标："AI 能否稳定驱动 ERP 操作闭环"。技术栈确定为 React + Vite 前端、FastAPI + Python 后端、OpenAI 原生 Tool Calling API。MVP 阶段使用 Mock ERP 内存数据，不接入真实 ERP 系统。

## Goals / Non-Goals

**Goals:**

- 实现 LLM 原生 Tool Calling 驱动的 Agent 核心循环
- 实现 SAFE/CAUTION/DANGER 三级风险分级的 Tool 执行策略
- 实现 DANGER 级别操作的审批确认机制（每个操作独立展示）
- 实现前端会话上下文管理（localStorage 持久化，N=6 轮窗口）
- 实现统一错误模型（AgentError + 四层错误码）
- 实现 Mock ERP 完整数据模型（orders/inventory/suppliers/counter）
- 覆盖 8 个 MVP 验证场景（查询/创建/推理/异常/批量/修改/取消/多操作审批）

**Non-Goals:**

- 不实现工作流引擎
- 不实现多 ERP 真实集成
- 不实现权限系统（RBAC）
- 不实现 RAG 知识库
- 不实现流式 UI
- 不实现 RPA 自动化
- 不实现微服务架构
- 不实现审批状态持久化（MVP 使用内存暂存）

## Decisions

### D1: 会话上下文 — 前端维护 + localStorage

**选择**: 前端维护对话历史，localStorage 持久化，每次请求携带最近 N=6 轮。

**替代方案**:
- 后端 session_id 维护：增加后端状态管理复杂度，MVP 不需要
- 前端 IndexedDB：容量更大但 API 复杂，MVP 阶段 localStorage 5MB 足够

**理由**: 前端维护保持后端无状态，localStorage API 简单，N=6 在上下文质量和 Token 消耗间取得平衡。

### D2: LLM 调用 — 原生 Tool Calling API

**选择**: 使用 OpenAI 原生 Tool Calling API（tools + tool_choice 参数）。

**替代方案**:
- 自定义 JSON 解析：模型无关但格式不可靠，需 few-shot 示例，容易出错
- LangGraph：功能强大但引入重依赖，MVP 阶段过度

**理由**: 原生 API 提供结构化保证、内置参数校验、自动重试机制，可靠性远高于自定义解析。

### D3: 写入安全 — CAUTION 限额 + 可配置

**选择**: CAUTION 级别（create_order 等）执行前检查数量限制，默认 max_items=5，通过 config.py 配置。

**理由**: 防止 LLM 幻觉导致批量创建，限额可配置为后续调整留空间。

### D4: 错误处理 — 统一 AgentError + 四层错误码

**选择**: 定义 AgentError 类，包含 code/message/detail/source/recoverable 五个字段。错误码前缀：LLM_/TOOL_/DATA_/SYS_。

**理由**: 统一错误模型让前端可以根据 error.code 做差异化展示，recoverable 标记帮助决定是否允许重试。

### D5: 副作用审批 — DANGER 级别需用户确认

**选择**: DANGER 级别 Tool（update_order/delete_order/cancel_order/adjust_inventory）执行前暂存到内存，返回 pending_action 给前端展示审批卡片，用户确认后通过 /chat/confirm 执行。每个操作独立展示，独立确认/拒绝。

**替代方案**:
- 多操作合并审批：交互复杂，用户无法选择性确认
- 自然语言拒绝：增加 LLM 理解复杂度，MVP 仅支持按钮操作

**理由**: 独立展示让用户对每个高风险操作有明确知情权，避免误操作。内存暂存 + TTL(5分钟) 在 MVP 阶段足够。

### D6: Mock ERP 数据模型 — 完整业务实体

**选择**: 实现 orders（含状态机）、inventory（含可用/预留）、suppliers、order_counter 四个数据实体。

**理由**: 覆盖所有 8 个 MVP 验证场景所需的数据支撑，订单状态机确保变更操作的合法性校验。

### D7: 前端架构 — 单页 ChatPage + 会话侧栏 + 审批卡片

**选择**: 单页面结构，左侧可折叠会话列表，右侧聊天区域含审批卡片组件。使用 React + Vite + 原生 CSS，不引入 UI 库。

**理由**: MVP 最小化依赖，原生 CSS 足够实现所需样式，会话侧栏和审批卡片作为独立组件按功能拆分。

## Risks / Trade-offs

- **[LLM 调用延迟]** DANGER 操作需两次 LLM 调用（决策 + 审批后生成回复）→ MVP 可接受，后续可优化为审批后直接拼接结果
- **[审批状态丢失]** 内存暂存 pending_action，服务重启后丢失 → 前端显示"操作已过期"提示，用户重新发起即可
- **[Token 消耗]** 每次请求携带 6 轮历史 → 单次约 2000-4000 tokens，MVP 阶段成本可控
- **[localStorage 容量]** 5MB 限制 → 单会话约 50KB，可存储约 100 个会话，足够 MVP 使用
- **[无权限控制]** 任何用户可执行所有操作 → MVP 阶段信任单一用户，Phase 4 引入 RBAC
- **[Mock 数据不持久]** 服务重启数据重置 → MVP 可接受，Phase 2 引入 PostgreSQL
