## Why

当前 `add-skill-framework-yaml-workflow` 已实现 Skill 框架的核心能力（意图匹配、handler/YAML 工作流执行、5 个 API 端点），但 Skill 行为对用户和审计**完全不可见**：
- 前端 SSE 事件流中只有 `tool_call` / `tool_result`，无 `skill_matched` / `workflow_step` / `skill_failed`，用户看不到 Skill 命中和工作流步骤进度
- 日志 jsonl 缺失 skill_* 事件类型，事后审计无法还原 Skill 触发的工具调用链
- `ToolStatusCard` 组件已存在但**未在 ChatPage 集成**，`need_more_info` 续谈路径无任何标识，失败也仅返回通用错误

需要新增 Skill 可观测性能力，让用户实时看到 Skill 命中 + workflow 步骤进度，让审计能完整还原 Skill 行为。

## What Changes

- **新增** `app/skills/observability.py` 模块，提供 `SkillObservability` 助手类（封装 SSE 事件 + 日志写入）
- **修改** `app/agent_logger.py`：新增 4 个日志方法 `log_skill_matched` / `log_workflow_step` / `log_workflow_result` / `log_skill_failed`
- **修改** `app/agent.py`：在 Skill 路径 4 个关键节点 emit SSE 事件（`skill_matched` / `workflow_step` / `workflow_result` / `skill_failed`）并写日志
- **修改** `frontend/src/ToolStatusCard.jsx`：扩展为 `SkillCard.jsx`，新增 props `skill_name` / `category` / `workflow_steps`（折叠式 step list）
- **修改** `frontend/src/ChatPage.jsx`：注册 `onSkillMatched` / `onWorkflowStep` / `onSkillFailed` 回调；流式中实时更新 `message.skillMatched` / `message.workflowSteps` / `message.skillFailed`
- **修改** `frontend/src/StreamingMessage.jsx`：在 tool-call-sequence 上方插入 `SkillCard`（命中时显示）；失败时复用 `error-message-banner` 红色横幅
- **修改** `app/main.py`：在 `chat` 与 `stream_chat` 的 Skill 路径里将 SSE `on_event` 注入到 `SkillObservability`（按 session 区分）
- **新增** `correlation_id` 字段：每个 Skill 执行生成 UUID，前端展示 + 日志写入，关联 Skill 命中 / workflow steps / 最终结果

## Capabilities

### New Capabilities

- `skill-sse-events`: Agent 在 Skill 路径关键节点 emit 新 SSE 事件（`skill_matched` / `workflow_step` / `workflow_result` / `skill_failed`）
- `skill-log-events`: SessionLogger 新增 4 个方法记录 skill_* 事件类型，含 prompt/instruction 截断 200 字符
- `skill-frontend-display`: 新增 `SkillCard` React 组件，标题含 `🎯 Skill: {name}` 标识，折叠式 step list 显示 workflow 步骤
- `skill-info-banner`: 消息体顶部命中标识条（含 skill 名称 + 分类 + 工具列表），流式中与完成后均显示
- `skill-workflow-progress`: workflow 步骤进度展示（流式中实时追加步骤状态 `pending` → `completed` / `failed`）
- `skill-failure-rendering`: Skill 失败时复用 `error-message-banner` 样式，显示 `SKILL_EXECUTION_FAILED` 错误（含 skill 名称 + 错误详情截断）
- `skill-need-more-info-display`: `need_more_info` 续谈标识，消息体顶部显示 "💬 Skill 追问中" 标识条，让用户区分意图
- `skill-correlation-id`: 每个 Skill 执行生成 UUID `skill_exec_<hex>`，跨 SSE 事件 / 日志 / 前端展示保持一致

### Modified Capabilities

- `agent-core`: chat/stream_chat 在 Skill 命中后 emit `skill_matched` SSE 事件；每完成一个 workflow step emit `workflow_step`；失败 emit `skill_failed`；成功 emit `workflow_result`（与现有 tool_call 事件并存，不替换）
- `prompt-config`: `build_system_prompt` 调用时记录 `skill_fragment_applied=true/false` 到日志（用于审计是否注入了 skill 指引）
- `error-handling`: 新增 `SKILL_EXECUTION_FAILED` 在前端的展示约定：错误消息含 skill 名称、recoverable=true、code 来源 `skill`（spec 层面已存在，实现层增加前端展示路径）

## Impact

- **后端新增文件**：`app/skills/observability.py`（~80 行，封装 SSE 事件 + 日志调用 + correlation_id 生成）
- **后端修改文件**：
  - `app/agent_logger.py`（+~40 行，4 个新方法）
  - `app/agent.py`（+~30 行，Skill 路径 4 个 emit 节点 + correlation_id 传递）
  - `app/main.py`（+~15 行，SkillObservability 注入 stream_chat 回调）
- **前端新增文件**：`frontend/src/SkillCard.jsx`（~100 行，复用 ToolStatusCard 的折叠交互）
- **前端修改文件**：
  - `frontend/src/ChatPage.jsx`（+~50 行，3 个新回调 + message 数据结构扩展）
  - `frontend/src/StreamingMessage.jsx`（+~20 行，SkillCard 嵌入 + 错误横幅复用）
  - `frontend/src/App.css`（+~30 行，skill-card / skill-info-banner / skill-failure 样式）
- **数据契约扩展**（后端 SSE 事件 + 前端 message）：
  - 新增 SSE 事件：`skill_matched` / `workflow_step` / `workflow_result` / `skill_failed`
  - 新增 message 字段：`skillMatched` / `workflowSteps` / `skillFailed` / `skillCorrelationId`
- **日志事件类型新增**：4 种（`skill_matched` / `workflow_step` / `workflow_result` / `skill_failed`）
- **API 行为不变**：不修改现有 `/chat` / `/chat/stream` / `/api/skills/*` 端点签名；仅在响应中**新增** SSE 事件类型（向后兼容）
- **前端兼容性**：流式模式新增 3 个 onEvent 回调（`onSkillMatched` / `onWorkflowStep` / `onSkillFailed`），同步模式无需改动
- **性能影响**：每条 Skill 路径增加 4 次 `logger._write` + 4 次 SSE emit；单次 < 1ms；无明显性能损耗
- **可观测性增强**：用户能实时看到 Skill 命中 + workflow 步骤进度；审计可还原完整 Skill 行为链（含中间步骤）
- **不修改 MCP / ERP 客户端层 / 不影响现有审批流**

## 验证方案

- **单元测试**（Python）：SkillObservability.correlation_id 唯一性、log_skill_* 各方法字段正确性、prompt 截断 200 字符
- **集成测试**（uvicorn + curl）：
  - `POST /chat/stream` 触发 Skill 路径，验证 SSE 事件流含 `skill_matched` / `workflow_step` 等新事件
  - 日志 jsonl 中验证 `skill_*` 事件类型 + correlation_id 关联
- **前端验证**（手动）：在浏览器中触发 Skill 场景，验证 SkillCard 折叠式展示、错误横幅、need_more_info 标识
- **回归验证**：现有 `tool_call` / `tool_result` SSE 事件不变；现有错误码展示不变
