## Context

### 背景

`add-skill-framework-yaml-workflow` 已实现 Skill 框架运行时（base/loader/registry/executor/validator 五个模块 + 5 个 API 端点 + 3 个 skill 数据），但 Skill 行为对**用户**和**审计**完全不可见：

- 前端 [StreamingMessage.jsx:30-39](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/frontend/src/StreamingMessage.jsx#L30-L39) 仅展示 `toolEvents`（tool 名），无 Skill 命中 / workflow 步骤进度
- 后端 [agent.py:120-198](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/app/agent.py#L120-L198) Skill 路径调用 `SkillExecutor.execute()` 后**未 emit 任何 SSE 事件**给前端
- 日志 [agent_logger.py:69-126](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/app/agent_logger.py#L69-L126) 现有 8 种事件类型（`session_start` / `llm_request` / `llm_response` / `tool_call` / `tool_result` / `approval_*` / `error` / `stream_chunk`），无 `skill_*` 事件
- 已有 [ToolStatusCard.jsx](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/frontend/src/ToolStatusCard.jsx) 组件但**未在 ChatPage 集成**
- `need_more_info` 续谈路径在 agent.py 实现完整，但前端无法区分"Skill 追问"与"普通 LLM 续谈"

### 设计输入

- 上游设计：[docs/design-skill-plan-c.md](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/docs/design-skill-plan-c.md)（Skill 框架）
- 上游设计：[openspec/changes/add-skill-framework-yaml-workflow/design.md](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/openspec/changes/add-skill-framework-yaml-workflow/design.md)
- 用户决策（基于 explore 阶段）：
  - **范围**：完整审计级（skill_matched + workflow_step + workflow_result + skill_failed 全部事件 + correlation_id 关联）
  - **样式**：折叠式 step list（复用 ToolStatusCard 折叠交互）
  - **时序**：分阶段（Phase 1 后端 → Phase 2 前端 → Phase 3 失败/need_more_info）

### 约束

- 现有 API 端点签名不变（向后兼容）
- 现有 SSE 事件类型（`tool_call` / `tool_result` / `reply_chunk` / `done`）不变
- 日志 jsonl 格式不变（仅新增事件类型）
- 不修改 MCP/ERP 客户端层
- 不影响审批流

## Goals / Non-Goals

**Goals:**

- 在 Skill 路径 4 个关键节点 emit 新 SSE 事件给前端
- SessionLogger 新增 4 个 `log_skill_*` 方法，支持完整审计
- 前端展示 Skill 命中 + workflow 步骤进度（折叠式）
- 失败时显示红色 `SKILL_EXECUTION_FAILED` 错误横幅
- `need_more_info` 续谈有明确标识
- correlation_id 跨 SSE / 日志 / 前端保持一致
- 分阶段实施，每阶段可独立验证

**Non-Goals:**

- 不修改现有 `tool_call` / `tool_result` 事件类型
- 不实现 Skill 性能监控 / 指标聚合（仅基础审计）
- 不实现前端可视化编辑器（仅展示）
- 不实现多 Skill 并发执行的展示（当前串行）
- 不实现 Skill 调试模式（replay 完整 workflow）
- 不修改 MCP/ERP 客户端层
- 不修改现有 `tool_status_card` 组件（新增 `skill_card`，共存）

## Decisions

### D1. 新增 `SkillObservability` 助手类（封装 SSE + 日志）

**决策**：在 `app/skills/observability.py` 新增 `SkillObservability` 类，封装 `correlation_id` 生成 + SSE `on_event` 回调 + `SessionLogger` 调用。

**替代方案**：
- ❌ 在 agent.py 直接 emit + 写日志：散落在 4 个分支，难以维护
- ✅ 助手类统一接口：`obs = SkillObservability(logger, on_event)` → `obs.skill_matched(skill)` / `obs.workflow_step(...)` / `obs.workflow_result(...)` / `obs.skill_failed(...)`

**理由**：单一职责；后续 Phase 3 的 need_more_info / 失败路径也复用同一类

### D2. correlation_id 格式：`skill_exec_<12 hex>`

**决策**：每次 Skill 执行生成 UUID 截取前 12 位，格式 `skill_exec_a1b2c3d4e5f6`。

**替代方案**：
- ❌ 全 UUID（36 字符）：日志冗长
- ❌ 纯递增数字：跨进程冲突
- ✅ 12 hex 字符：足够唯一（48 位熵），紧凑可读

**理由**：12 hex ≈ 10^14 唯一值，单进程内不重复；前缀 `skill_exec_` 自带语义

### D3. SSE 事件命名：`skill_*` 前缀（与现有 `tool_*` 区分）

**决策**：4 个新 SSE 事件 `skill_matched` / `workflow_step` / `workflow_result` / `skill_failed`，与现有 `tool_call` / `tool_result` 并存。

**替代方案**：
- ❌ 复用 `tool_call` 事件：会污染现有前端逻辑
- ❌ 单独命名空间 `sse.skill.*`：过深，前端需额外解析
- ✅ 平铺命名 `skill_*`：与 `tool_*` 平行，前端直接 `onSkillMatched` 钩子

**理由**：事件命名一致性（`tool_*` / `skill_*` / `approval_*` 三大族）

### D4. workflow_step 事件：每步完成后 emit（不发中间态）

**决策**：仅在 `tool_call` / `prompt` 步骤**完成**时 emit `workflow_step`，status=completed/failed/pending_approval。不发 `pending` 状态。

**替代方案**：
- ❌ 每步开始 + 完成各发一次：SSE 流量翻倍
- ❌ 仅发完成：丢失进度感
- ✅ 仅发完成（含 elapsed_ms）：前端可见"已完成"但无 in-progress

**理由**：减少 SSE 流量；前端"折叠式 step list"默认折叠，无需 in-progress 动画

### D5. 前端 SkillCard 组件：复用 ToolStatusCard 折叠交互

**决策**：新建 `frontend/src/SkillCard.jsx`，结构与 `ToolStatusCard` 镜像：
- Header: `🎯 Skill: {name}` + 状态徽章
- Body（折叠）: workflow 步骤列表（每行 step_id + type + tool + status）

**替代方案**：
- ❌ 修改 ToolStatusCard 接受 skill props：耦合两个不同概念
- ✅ 独立 SkillCard：清晰职责分离
- ❌ 全新设计风格：违反"折叠式"决策

**理由**：用户已选折叠式；新组件复用 `useState(expanded)` 交互模式

### D6. need_more_info 标识：💬 Skill 追问中 标识条

**决策**：消息体顶部新增横幅"💬 Skill {name} 追问中"，独立于 SkillCard。

**替代方案**：
- ❌ 复用 SkillCard 加新字段：混淆"工作流执行中"与"等待用户输入"
- ✅ 独立标识条：清晰区分 Skill 状态（执行中 / 等待 / 失败）

**理由**：need_more_info 是一种 Skill 暂停状态（handler 已完成部分步骤后等待用户），独立展示更易理解

### D7. 日志脱敏：prompt_fragment 完整记录（不脱敏）

**决策**：`skill_matched` 日志的 `prompt_fragment` 字段完整记录（不脱敏、不截断），其他字段（description / instruction）截断 200 字符。

**替代方案**：
- ❌ 全部截断：审计丢失关键信息
- ❌ 全部脱敏：调试困难
- ✅ prompt_fragment 完整 + 其他截断：平衡审计与日志体积

**理由**：prompt_fragment 是 Skill 设计者写死的、非用户输入、不含 PII

### D8. 后端 emit 位置：在 agent.py 4 个分支开头

**决策**：`SkillObservability` 在 [agent.py:chat()](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/app/agent.py) 的 4 个分支开头调用：
1. Skill 命中（after `match_skill()` 成功）→ `skill_matched`
2. workflow step 完成（executor 回调中）→ `workflow_step`（实际在 executor.py 内）
3. workflow 成功结束 → `workflow_result`
4. workflow 失败 → `skill_failed`

**替代方案**：
- ❌ 全部在 executor.py 内 emit：executor 不应感知 SSE on_event
- ✅ agent.py 编排 emit，executor 通过回调通知：解耦

**理由**：executor 保持纯函数（无 SSE 副作用）；agent.py 负责"何时 emit"

### D9. executor.py 通过回调函数通知 workflow_step 完成

**决策**：`SkillExecutor._execute_yaml_workflow` 接受可选参数 `on_step_complete: Optional[Callable]`，每完成一步调用。

**替代方案**：
- ❌ executor 直接 emit SSE：耦合副作用
- ❌ agent.py 轮询 executor 状态：不必要复杂度
- ✅ 回调函数：解耦 + 灵活

**理由**：executor 仍是纯计算；agent.py 注入回调处理 SSE + 日志

### D10. 前端 message 扩展：新增 3 个字段（向后兼容）

**决策**：`message` 对象新增 `skillMatched` / `workflowSteps` / `skillFailed` 三个字段，**可选**（默认 undefined）。

**替代方案**：
- ❌ 强制所有 message 包含 skill 字段：污染非 Skill 场景
- ✅ 可选字段：未匹配 Skill 的 message 保持原结构

**理由**：纯增量改动，旧代码逻辑不受影响

## Risks / Trade-offs

| # | 风险 / 权衡 | 影响 | 缓解 |
|---|------------|------|------|
| R1 | SSE 事件类型增多，前端需扩展回调 | 中 | Phase 1 后端先发，前端 in-flight 时只忽略未处理事件；后续 Phase 2 集中实现 |
| R2 | correlation_id 跨事件一致性 | 中 | `SkillObservability` 同一实例持有 `self.correlation_id`，所有 emit 使用同一 ID；日志写入用同一字段 |
| R3 | 失败时若 `on_event` 回调异常，不影响主流程 | 中 | agent.py 用 `try/except` 包裹 SSE emit；日志写入已有 `try/except: pass` 兜底 |
| R4 | 日志 jsonl 行长度增长 | 低 | prompt_fragment 完整记录（~500 字符），其他字段截断 200 字符；总行 < 2KB |
| R5 | 折叠式 step list 需点击展开，不如 inline 直观 | 低 | 头部加 step 进度文本（如 "2/3 步已完成"），无需展开也能感知 |
| R6 | 复用 ToolStatusCard CSS 类 vs 新建 skill-card CSS | 低 | 共存而非复用，避免类名冲突；App.css 新增独立样式 |
| R7 | need_more_info 标识条与 Skill 命中条同时存在 | 低 | 标识条互斥：要么"Skill 命中 + 执行中"、要么"Skill 追问中"、要么"Skill 失败" |
| R8 | 阶段实施期间，事件发出但前端未处理 | 低 | 前端默认忽略未知事件类型；不阻塞现有 tool_call 等流程 |
| R9 | `SkillObservability` 持有 `on_event` 回调引用，stream_chat 闭包 | 低 | 仅在 chat/stream_chat 函数内创建局部实例，函数返回即释放 |

## Migration Plan

### Phase 1：后端 SSE + 日志

1. **新增** `app/skills/observability.py`（~80 行）：
   - `class SkillObservability(logger, on_event)`
   - `skill_matched(skill)` → emit SSE + log
   - `workflow_step(skill, step_id, type, status, result?)` → emit SSE + log
   - `workflow_result(skill, success, need_approval, need_more_info, step_count)` → emit SSE + log
   - `skill_failed(skill, error)` → emit SSE + log
2. **修改** `app/agent_logger.py`：新增 4 个 `log_skill_*` 方法
3. **修改** `app/skills/executor.py`：`_execute_yaml_workflow` 接受 `on_step_complete` 回调
4. **修改** `app/agent.py`：chat() 在 Skill 路径创建 `SkillObservability` 实例并传入
5. **单测**：单元测试 4 个 emit 函数的字段正确性 + correlation_id 一致性

### Phase 2：前端 SkillCard + 折叠式 step list

1. **新增** `frontend/src/SkillCard.jsx`（~100 行）：
   - Header: `🎯 Skill: {name}` + 状态徽章 + 折叠箭头
   - Body: workflow 步骤列表（`step_id` + `type` + `tool` + `status`）
2. **修改** `frontend/src/ChatPage.jsx`：
   - 注册 `onSkillMatched` / `onWorkflowStep` / `onSkillFailed` 3 个回调
   - 更新 `message` 数据结构（添加 3 个字段）
3. **修改** `frontend/src/StreamingMessage.jsx`：
   - 在 `toolEvents` 上方插入 `<SkillCard>`（命中时显示）
   - 完成后在 `completedTools` 旁展示 SkillCard 折叠状态
4. **修改** `frontend/src/App.css`：新增 `.skill-card` / `.skill-info-banner` 样式

### Phase 3：失败 / need_more_info 标识

1. **修改** `app/agent.py`：在 need_more_info / failure 分支调用 `SkillObservability` 对应方法
2. **修改** `frontend/src/StreamingMessage.jsx`：
   - `skillFailed` 字段非空时显示红色 `error-message-banner` 复用样式
   - `needMoreInfo` 标识条"💬 Skill {name} 追问中"
3. **集成测试**：触发 need_more_info 场景，验证前端展示

### 回滚策略

- Phase 1 回滚：删除 `observability.py` 模块，agent.py 移除 emit 调用；现有 tool_call 等流程不变
- Phase 2 回滚：删除 `SkillCard.jsx`，ChatPage/StreamingMessage 移除 SkillCard 引用；新增 3 个 message 字段默认 undefined 不影响旧逻辑
- Phase 3 回滚：移除失败/need_more_info 标识相关代码

## Open Questions

| # | 问题 | 候选方案 | 倾向 |
|---|------|---------|------|
| Q1 | workflow_step 日志是否记录 result 字段？ | A. 完整记录（审计可还原）/ B. 只记 status + step_id | A（完整审计级）|
| Q2 | correlation_id 是否写入每个 SSE 事件？ | A. 是（所有事件）/ B. 仅在 workflow_result 携带 | A（前端可关联所有事件）|
| Q3 | 失败时是否回放导致失败的 step_id？ | A. 携带 failed_step_id / B. 仅 error_message | A（便于定位）|
| Q4 | SkillCard 默认展开还是折叠？ | A. 默认折叠 / B. 默认展开 | **用户已选折叠** |
| Q5 | 是否需要"跳过 Skill 提示"开关？ | A. 是 / B. 否 | B（无需求驱动）|
| Q6 | 失败时是否仍显示 SkillCard（折叠）？ | A. 是（标红）/ B. 否 | A（保持上下文）|
