## Why

当前缺少一个可验证的 ERP Agent 系统，无法证明"AI 能否稳定驱动 ERP 操作闭环"。需要构建一个 MVP，通过自然语言驱动 ERP 查询、写入、批处理等操作，验证 LLM + Tool Calling 架构在 ERP 场景下的可行性。

## What Changes

- 新增 React + Vite 前端，包含聊天界面、会话管理侧栏、审批卡片组件
- 新增 FastAPI 后端，实现 Agent 核心循环（LLM 原生 Tool Calling API）
- 新增 Tool 系统（8 个 Tool：4 SAFE + 1 CAUTION + 4 DANGER），含风险分级与限额机制
- 新增副作用操作审批确认机制（DANGER 级别 Tool 需用户确认后执行，每个操作独立展示）
- 新增会话上下文管理（前端 localStorage 持久化，每次请求携带最近 N=6 轮历史）
- 新增统一错误模型（AgentError + 错误码体系，覆盖 LLM/Tool/数据/系统四层）
- 新增 Mock ERP 数据层（orders/inventory/suppliers/counter 完整数据模型）
- 新增 API 端点：`POST /chat`（含 history）、`POST /chat/confirm`（审批确认）

## Capabilities

### New Capabilities

- `chat-api`: 聊天 API 端点，接收用户消息+历史上下文，返回 Agent 回复，支持 pending_action 审批流
- `agent-core`: Agent 核心循环，LLM 原生 Tool Calling 驱动，含 SAFE/CAUTION/DANGER 三级风险路由
- `tool-system`: Tool 定义、注册、执行框架，8 个 ERP Tool，含限额检查与风险分级配置
- `approval-flow`: 副作用操作审批机制，DANGER 级别暂存+确认/拒绝，内存 TTL 过期管理
- `session-context`: 会话上下文管理，前端 localStorage 持久化，N 轮窗口截取，新建/切换/删除会话
- `error-handling`: 统一错误模型 AgentError，LLM/TOOL/DATA/SYS 四层错误码，可恢复性标记
- `mock-erp`: Mock ERP 数据层，orders/inventory/suppliers/counter 完整数据模型与状态机
- `chat-ui`: React 聊天界面，含会话侧栏、审批卡片组件、消息渲染、localStorage 持久化

### Modified Capabilities

## Impact

- **后端新增文件**：`main.py` `agent.py` `llm.py` `tools.py` `mock_erp.py` `config.py` `errors.py` `approval.py`
- **前端新增**：React + Vite 项目，ChatPage + SessionManager + ApprovalCard 组件
- **API 变更**：新增 `POST /chat`（含 history 字段）、`POST /chat/confirm` 两个端点
- **外部依赖**：OpenAI Python SDK（LLM 调用）、FastAPI、React + Vite
- **数据层**：Mock ERP 内存字典，无数据库依赖
