# Tasks: add-skill-observability

> 对应变更：`openspec/changes/add-skill-observability/`
> 任务拆分策略：**按 spec 维度拆分到独立文件**，主 `tasks.md` 仅保留跨切面任务（设置/测试/文档/审计）。
> 实施阶段：Phase 1（后端 SSE+日志）→ Phase 2（前端 SkillCard+折叠式）→ Phase 3（失败/need_more_info 标识）。

## 任务文件索引

### New Capabilities（8 个新能力）

| Spec | 任务文件 | 阶段 | 覆盖范围 |
|------|---------|------|---------|
| [skill-sse-events](specs/skill-sse-events/spec.md) | [tasks/skill-sse-events.md](tasks/skill-sse-events.md) | Phase 1 | observability 助手类 + 4 个 emit 方法 + 回调注册 |
| [skill-log-events](specs/skill-log-events/spec.md) | [tasks/skill-log-events.md](tasks/skill-log-events.md) | Phase 1 | 4 个 log_skill_* 方法 + 200 字符截断 |
| [skill-frontend-display](specs/skill-frontend-display/spec.md) | [tasks/skill-frontend-display.md](tasks/skill-frontend-display.md) | Phase 2 | SkillCard 折叠式 step list + 步骤进度 |
| [skill-info-banner](specs/skill-info-banner/spec.md) | [tasks/skill-info-banner.md](tasks/skill-info-banner.md) | Phase 2 | 命中标识条 + 工具 chips |
| [skill-workflow-progress](specs/skill-workflow-progress/spec.md) | [tasks/skill-workflow-progress.md](tasks/skill-workflow-progress.md) | Phase 2 | 步骤进度计算 + type 区分 + elapsed_ms |
| [skill-failure-rendering](specs/skill-failure-rendering/spec.md) | [tasks/skill-failure-rendering.md](tasks/failure-rendering.md) | Phase 3 | 失败红色横幅 + SkillCard 互斥 |
| [skill-need-more-info-display](specs/skill-need-more-info-display/spec.md) | [tasks/skill-need-more-info-display.md](tasks/skill-need-more-info-display.md) | Phase 3 | 续谈标识 + 输入区 hint |
| [skill-correlation-id](specs/skill-correlation-id/spec.md) | [tasks/skill-correlation-id.md](tasks/skill-correlation-id.md) | Phase 1 | correlation_id 生成 + 跨事件注入 |

### Modified Capabilities（3 个修改能力）

| Spec | 任务文件 | 阶段 | 覆盖范围 |
|------|---------|------|---------|
| [agent-core](specs/agent-core/spec.md) | [tasks/agent-core.md](tasks/agent-core.md) | Phase 1+2 | chat() Skill 路径 emit + contextvars 注入 |
| [prompt-config](specs/prompt-config/spec.md) | [tasks/prompt-config.md](tasks/prompt-config.md) | Phase 1 | skill_fragment_applied 日志 |
| [error-handling](specs/error-handling/spec.md) | [tasks/error-handling.md](tasks/error-handling.md) | Phase 1 | SKILL_EXECUTION_FAILED 前端渲染路径 |

### 跨切面任务（本文件）

| 组 | 任务范围 | 阶段 |
|----|---------|------|
| 1 | Setup & 依赖（无新增依赖） | Phase 0 |
| 2 | Validation & Smoke Testing | Phase 1+2+3 |
| 3 | Documentation | Phase 3 |
| 4 | **sub-agent 任务审计**（config.yaml 强制最后任务） | 实施完成后 |

---

## 1. Setup & 依赖

- [x] 1.1 确认无新增 Python/Node 依赖（observability.py 仅用 stdlib + uuid + contextvars）
- [x] 1.2 确认无新增 npm 依赖（SkillCard.jsx 仅用 useState + 现有 hooks）
- [x] 1.3 检查 `app/skills/observability.py` 路径不存在（如存在则提示冲突）
- [x] 1.4 检查 `frontend/src/SkillCard.jsx` 路径不存在
- [x] 1.5 检查 `frontend/src/SkillInfoBanner.jsx` 路径不存在

---

## 2. Validation & Smoke Testing

### 2.1 Phase 1（后端 SSE + 日志）验证
- [x] 2.1.1 启动后端，验证 `GET /health` 返回 200
- [x] 2.1.2 发送 `POST /chat` 触发 query-order-search skill，验证 chat 响应正常
- [x] 2.1.3 检查日志文件 `logs/<date>_<session>.jsonl` 包含 `skill_matched` 事件（correlation_id 一致）
- [x] 2.1.4 触发 query-order-edit-address skill（带新地址），验证日志含 `workflow_result` + need_approval=True
- [x] 2.1.5 触发 batch-query-order（YAML workflow），验证日志含多条 `workflow_step` 事件（每步一个）
- [x] 2.1.6 触发 skill 失败场景，验证日志含 `skill_failed` 事件
- [x] 2.1.7 单元测试：SkillObservability 5 个方法 emit + log 字段正确
- [x] 2.1.8 单元测试：100 次生成 correlation_id 无重复
- [x] 2.1.9 单元测试：prompt_fragment 完整保留 / instruction 截断 200 / error_detail 截断 200

### 2.2 Phase 2（前端 SkillCard）验证
- [x] 2.2.1 前端服务器启动成功（http://localhost:5173）
- [x] 2.2.2 后端服务器启动成功（http://127.0.0.1:8001）- main.py import 修复
- [ ] 2.2.3 浏览器触发 skill 场景，验证 SkillCard 折叠式卡片显示（需手动验证）
- [ ] 2.2.4 点击 SkillCard header，验证 step list 展开（需手动验证）
- [ ] 2.2.5 验证 SkillInfoBanner 在消息体顶部显示（含 category badge + tools chips）（需手动验证）
- [ ] 2.2.6 验证 correlation_id 在 SkillCard footer 显示（展开时）（需手动验证）
- [ ] 2.2.7 验证进度文本"X/Y 步已完成"显示正确（需手动验证）
- [ ] 2.2.8 验证 5+ tools 时显示 "+N more"（需手动验证）
- [ ] 2.2.9 单元测试：SkillCard 组件 props 渲染（待实施）

### 2.3 Phase 3（失败/need_more_info）验证
- [ ] 2.3.1 触发 skill 失败场景，验证红色 `error-message-banner` 显示在消息体顶部
- [ ] 2.3.2 验证错误消息含 skill 名称 + 错误详情 + 错误码 + "可重试"提示
- [ ] 2.3.3 触发 need_more_info 场景（缺新地址），验证蓝色"💬 Skill 追问中"标识显示
- [ ] 2.3.4 验证 input 区 placeholder 切换为"请回复 Skill 追问"
- [ ] 2.3.5 验证 SkillCard 显示 ⏸️ 等待您回复 徽章 + 下一未执行步骤虚线边框
- [ ] 2.3.6 用户提交回复后，验证下一 message 触发新的 skill 匹配，清除 hint

### 2.4 回归验证
- [ ] 2.4.1 现有 tool_call / tool_result SSE 事件不变（非 Skill 路径）
- [ ] 2.4.2 现有 tool_status_card 组件不变（与 SkillCard 共存）
- [ ] 2.4.3 现有审批流 /chat/confirm 不受影响
- [ ] 2.4.4 现有 9 个 ERP 工具调用不受影响
- [ ] 2.4.5 同步 /chat（非流式）端点不受影响（observability 走 contextvars 兼容同步/异步）

---

## 3. Documentation

- [ ] 3.1 更新 `docs/architecture.md` 添加 SkillObservability 模块节点
- [ ] 3.2 更新 `docs/skill-authoring.md` 新增章节"SSE 事件契约"（4 种 skill_* 事件 + payload）
- [ ] 3.3 更新 `docs/skill-authoring.md` 新增章节"日志事件"（5 种 skill_* 日志 + 截断规则）
- [ ] 3.4 更新 `README.zh.md` 提及 Skill 命中后消息体验升级（命中 banner + 步骤卡片）

---

## 4. sub-agent 任务审计（强制 — 最后一个任务）

> ⚠️ 依据 `c:\global-user-data\ai-workspace\openspec\config.yaml` 规则：
> `tasks 文档的最后一个任务必须为「sub-agent 任务审计任务」`

### 4.1 审计执行步骤
- [ ] 4.1.1 调用 `git diff HEAD` + `git status --untracked-files=all` 获取本次提案所有代码变更点
- [ ] 4.1.2 与本变更 `tasks.md`（含 `tasks/*.md` 11 个 per-spec 文件）逐项对照
- [ ] 4.1.3 输出审计报告 `openspec/changes/add-skill-observability/audit-report.md`，包含：
  - 任务完成度统计（已完成 / 未完成 / 跳过）
  - 每个文件变更点对应的任务编号映射
  - 增量变更 vs 既有代码的兼容性检查
  - 3 阶段实施完成度（Phase 1 / 2 / 3 独立验证）

### 4.2 严重问题标注（**必须**明确）
- [ ] 4.2.1 检查每条任务，标注以下任一情况：
  - **存在 Bug**：列出具体任务编号 + 涉及文件 + Bug 描述
  - **代码变更不完整**：列出未实现 / 部分实现的任务
  - **文件关联影响：改漏、改错**：跨文件影响未传递（如改了 SkillObservability 但未改 agent.py）
  - **变更实现与 tasks 描述不一致**：代码逻辑偏离任务描述
- [ ] 4.2.2 每条严重问题输出处理意见（修复 / 重做 / 接受偏差并说明理由）

### 4.3 审计报告交付
- [ ] 4.3.1 审计报告作为本变更归档前置条件
- [ ] 4.3.2 用户审阅审计报告 → 修复严重问题 → 重新审计 → 通过后归档
- [ ] 4.3.3 归档命令：`openspec archive add-skill-observability --yes`

### 4.4 审计报告模板

```markdown
# Audit Report: add-skill-observability

## 任务完成度
- 总任务数：~140
- 已完成：N
- 未完成：N
- 跳过：N
- 完成率：N%
- Phase 1 完成度：N/M
- Phase 2 完成度：N/M
- Phase 3 完成度：N/M

## 文件变更映射
| 任务编号 | 涉及文件 | 变更类型 | 状态 |
|---------|---------|---------|------|
| skill-sse-events/1.1.1 | app/skills/observability.py | 新建 | ✅ |
| skill-log-events/1.2.1 | app/agent_logger.py | 修改 | ✅ |
| ... | ... | ... | ... |

## 严重问题清单
### [BUG-001] <title>
- **任务编号**：skill-sse-events/2.1.4
- **涉及文件**：app/agent.py:135
- **问题描述**：...
- **处理意见**：...

## 兼容性验证
- 现有 tool_call SSE 事件不变：✅ / ❌
- ENABLE_SKILL=False 行为不变：✅ / ❌
- ToolStatusCard 与 SkillCard 共存：✅ / ❌
- 审批流不受影响：✅ / ❌
```

---

## 实施时间线（参考）

| 阶段 | 估算工时 | 依赖 |
|------|---------|------|
| Phase 1：observability + 4 个 log_skill_* + executor 回调 + agent 集成 | ~2-3 小时 | Setup |
| Phase 2：SkillCard + SkillInfoBanner + 3 个回调 + CSS | ~3-4 小时 | Phase 1 |
| Phase 3：失败/need_more_info 标识 + 输入区 hint | ~1-2 小时 | Phase 2 |
| 单元测试 + 集成测试 | ~1-2 小时 | Phase 1+2+3 |
| 文档 + 审计 | ~1 小时 | 全部 |
| **合计** | **~8-12 小时** | — |

按 config.yaml 规则"每个任务最大 2 小时"，每个 per-spec 任务文件已拆分为 ≤30-90 分钟的原子任务。
