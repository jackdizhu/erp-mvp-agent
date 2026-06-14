# Tasks: skill-workflow-progress

> 对应 spec: [skill-workflow-progress](../specs/skill-workflow-progress/spec.md)
> 实施阶段: Phase 2（前端 SkillCard + 折叠式 step list）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/ChatPage.jsx` | 修改 | +~25 | 注册 onWorkflowStep 回调 + 实时累加 message.workflowSteps |
| `frontend/src/SkillCard.jsx` | 修改 | +~30 | 步骤进度计算 + type 区分 + elapsed_ms 徽章 |

---

## 1. `frontend/src/ChatPage.jsx` — 实时累加步骤

### 1.1 回调函数
- [ ] 1.1.1 在 `handleStreamSend` 的 `callbacks` 中新增 `onWorkflowStep: (data) => { ... }`
- [ ] 1.1.2 回调体：检查是否已存在同 `step_id` 步骤，如有则更新 status / result，否则 push 新条目
- [ ] 1.1.3 关键点（spec）：同一 step_id 的 status 变化采用"in-place 更新"（避免重复行）

### 1.2 in-place 更新逻辑
- [ ] 1.2.1 `const existingIdx = msg.workflowSteps.findIndex(s => s.step_id === data.step_id);`
- [ ] 1.2.2 `if (existingIdx >= 0) msg.workflowSteps[existingIdx] = { ...msg.workflowSteps[existingIdx], ...data };`
- [ ] 1.2.3 `else msg.workflowSteps = [...msg.workflowSteps, data];`
- [ ] 1.2.4 关键点：使用新对象引用触发 React 重渲染

### 1.3 StepEvent 字段归一化
- [ ] 1.3.1 后端 SSE 字段映射到前端：
  - `step_id` → `step_id`
  - `type` → `type`
  - `tool` → `tool`
  - `instruction` → `instruction`
  - `status` → `status`
  - `result_summary` → `result_summary`
  - `elapsed_ms` → `elapsed_ms`

---

## 2. `frontend/src/SkillCard.jsx` — 步骤进度计算

### 2.1 进度计数
- [ ] 2.1.1 计算 `completed = workflow_steps.filter(s => s.status === 'completed').length`
- [ ] 2.1.2 计算 `failed = workflow_steps.filter(s => s.status === 'failed').length`
- [ ] 2.1.3 计算 `pending = workflow_steps.filter(s => s.status === 'pending_approval').length`
- [ ] 2.1.4 计算 `total = workflow_steps.length`

### 2.2 进度文本渲染
- [ ] 2.2.1 格式：`{completed}/{total} 步已完成`
- [ ] 2.2.2 若 `failed > 0` 追加：`（{failed} 失败）`
- [ ] 2.2.3 若 `pending > 0` 追加：`（{pending} 待审批）`
- [ ] 2.2.4 示例：`2/3 步已完成（1 失败）` / `3/3 步已完成` / `1/3 步已完成（1 待审批）`

### 2.3 步骤类型区分
- [ ] 2.3.1 tool_call 步骤：显示 `🔧 {tool_name}`（gear icon + monospace）
- [ ] 2.2.2 prompt 步骤：显示 `💬 prompt` + instruction 前 50 字符
- [ ] 2.2.3 instruction 截断：`{instruction.slice(0, 50)}{instruction.length > 50 ? '...' : ''}`

### 2.4 elapsed_ms 徽章
- [ ] 2.4.1 格式化函数：`{elapsed_ms < 1000 ? \`${elapsed_ms}ms\` : \`${(elapsed_ms/1000).toFixed(1)}s\`}`
- [ ] 2.4.2 颜色规则：< 5s gray / 5-10s orange / > 10s red

### 2.5 result_summary 显示
- [ ] 2.5.1 显示 `{result_summary.slice(0, 80)}{result_summary.length > 80 ? '...' : ''}`
- [ ] 2.5.2 颜色 muted gray（不抢眼）

### 2.6 失败步骤高亮
- [ ] 2.6.1 props `failed_step_id` 匹配时该行 CSS 类加 `failed`
- [ ] 2.6.2 已有 [skill-frontend-display spec: 2.6.1-2.6.2](../specs/skill-frontend-display/spec.md) 覆盖
