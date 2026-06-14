# Tasks: skill-frontend-display

> 对应 spec: [skill-frontend-display](../specs/skill-frontend-display/spec.md)
> 实施阶段: Phase 2（前端 SkillCard + 折叠式 step list）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/SkillCard.jsx` | 新建 | ~120 | 折叠式 SkillCard 组件（复用 ToolStatusCard 模式） |
| `frontend/src/App.css` | 修改 | +~40 | 新增 `.skill-card` / `.skill-step-row` / `.skill-correlation-id` 样式 |

---

## 1. `frontend/src/SkillCard.jsx` — 组件实现

### 1.1 组件骨架
- [ ] 1.1.1 导入 `useState` from 'react'
- [ ] 1.1.2 定义 `STATUS_LABELS` 常量（completed: "已完成", failed: "失败", pending_approval: "等待审批"）
- [ ] 1.1.3 定义 `STATUS_COLORS` 常量（completed: green, failed: red, pending_approval: purple）
- [ ] 1.1.4 关键点（设计 D5）：参考 ToolStatusCard 结构，但用独立 CSS 类 `.skill-card` 避免命名冲突

### 1.2 组件定义
- [ ] 1.2.1 `export default function SkillCard({ skill_name, category, description, tools, workflow_steps, correlation_id, failed_step_id }) {`
- [ ] 1.2.2 `const [expanded, setExpanded] = useState(false);`（默认折叠）
- [ ] 1.2.3 关键点：默认折叠符合设计决策（用户已选"折叠式"）

### 1.3 Header 渲染
- [ ] 1.3.1 渲染 `<div className="skill-card-header" onClick={() => setExpanded(!expanded)}>`
- [ ] 1.3.2 显示 `🎯` 图标 + `Skill: {skill_name}` 文本
- [ ] 1.3.3 显示 category badge（preset/custom 标签）
- [ ] 1.3.4 显示步骤进度文本 `2/3 步已完成`（在 CardStatus 之前或之后）
- [ ] 1.3.5 显示折叠箭头 `▶` / `▼`（CSS rotate 或字符切换）

### 1.4 步骤进度计算
- [ ] 1.4.1 `const completed = workflow_steps?.filter(s => s.status === 'completed').length || 0;`
- [ ] 1.4.2 `const total = workflow_steps?.length || 0;`
- [ ] 1.4.3 `const failed = workflow_steps?.filter(s => s.status === 'failed').length || 0;`
- [ ] 1.4.4 显示规则：`(completed + failed) / total` 文本；若有 failed 追加 `(N 失败)`

### 1.5 Body 渲染（折叠展开）
- [ ] 1.5.1 条件渲染 `{expanded && <div className="skill-card-body">}`
- [ ] 1.5.2 错误信息（如 failed）：`<div className="skill-error-section">{error_message}</div>`
- [ ] 1.5.3 步骤列表：`<div className="skill-step-list">` 渲染每步
- [ ] 1.5.4 每步渲染：`<div key={step.step_id} className={...failed_step_id === step.step_id ? "skill-step-row failed" : "skill-step-row"}>`
- [ ] 1.5.5 显示 step_id (bold) + type badge (prompt/tool_call) + tool 名（如果存在）
- [ ] 1.5.6 显示 result_summary（截断 80 字符）
- [ ] 1.5.7 显示 elapsed_ms 徽章（< 1s 显示 ms，> 1s 显示 s）

### 1.6 Correlation ID footer
- [ ] 1.6.1 当 `correlation_id` 存在时显示 `<div className="skill-correlation-id">🔗 {correlation_id}</div>`
- [ ] 1.6.2 添加 title 属性（hover tooltip）："Skill 执行追踪 ID，可在日志中按此 ID 检索完整事件链"

### 1.7 单元测试（≤ 1 小时，组件测试）
- [ ] 1.7.1 渲染最小 props（skill_name, workflow_steps=[]）：卡片可见，body 隐藏
- [ ] 1.7.2 模拟点击 header：body 展开显示
- [ ] 1.7.3 提供 3 个 workflow_steps（2 completed, 1 pending）：进度显示 "2/3 步已完成"
- [ ] 1.7.4 提供 failed_step_id="step2"：对应行红色高亮
- [ ] 1.7.5 correlation_id 显示在 footer

---

## 2. `frontend/src/App.css` 修改

### 2.1 .skill-card 基础样式
- [ ] 2.1.1 `.skill-card { border: 1px solid #c4b5fd; border-radius: 6px; margin: 8px 0; background: #faf5ff; }`
- [ ] 2.1.2 `.skill-card-header { padding: 8px 12px; display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }`
- [ ] 2.1.3 `.skill-card-header:hover { background: #f3e8ff; }`

### 2.2 步骤行样式
- [ ] 2.2.1 `.skill-step-list { padding: 8px 12px; }`
- [ ] 2.2.2 `.skill-step-row { padding: 4px 0; border-bottom: 1px dashed #e9d5ff; display: flex; gap: 6px; align-items: center; }`
- [ ] 2.2.3 `.skill-step-row.failed { border: 1px solid #fca5a5; background: #fef2f2; }`
- [ ] 2.2.4 `.skill-step-id { font-weight: 600; font-family: monospace; }`
- [ ] 2.2.5 `.skill-step-type { font-size: 11px; padding: 1px 6px; border-radius: 3px; background: #ede9fe; color: #6d28d9; }`
- [ ] 2.2.6 `.skill-step-tool { font-family: monospace; font-size: 12px; color: #4b5563; }`
- [ ] 2.2.7 `.skill-step-elapsed { font-size: 10px; color: #9ca3af; margin-left: auto; }`

### 2.3 Status 徽章样式
- [ ] 2.3.1 `.skill-status-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; color: white; }`
- [ ] 2.3.2 `.skill-status-completed { background: #10b981; }` / `.skill-status-failed { background: #ef4444; }` / `.skill-status-pending_approval { background: #8b5cf6; }`

### 2.4 Category 徽章 + 进度文本
- [ ] 2.4.1 `.skill-category-badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: #e0e7ff; color: #4338ca; }`
- [ ] 2.4.2 `.skill-progress-text { font-size: 11px; color: #6b7280; margin-left: auto; }`

### 2.5 Correlation ID 样式
- [ ] 2.5.1 `.skill-correlation-id { font-size: 10px; color: #9ca3af; font-family: monospace; padding: 4px 12px; border-top: 1px solid #e9d5ff; }`
