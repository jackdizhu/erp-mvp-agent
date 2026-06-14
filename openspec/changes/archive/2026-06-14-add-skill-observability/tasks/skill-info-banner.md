# Tasks: skill-info-banner

> 对应 spec: [skill-info-banner](../specs/skill-info-banner/spec.md)
> 实施阶段: Phase 2（前端 SkillCard + 折叠式 step list）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/SkillInfoBanner.jsx` | 新建 | ~80 | 命中标识条组件（独立于 SkillCard） |
| `frontend/src/StreamingMessage.jsx` | 修改 | +~15 | 在消息体顶部插入 SkillInfoBanner |
| `frontend/src/ChatPage.jsx` | 修改 | +~10 | 注册 onSkillMatched 回调 + 填充 message.skillMatched |
| `frontend/src/App.css` | 修改 | +~30 | `.skill-info-banner` 样式 |

---

## 1. `frontend/src/SkillInfoBanner.jsx` — 组件实现

### 1.1 组件定义
- [ ] 1.1.1 `export default function SkillInfoBanner({ skill_name, category, tools, onClick }) {`
- [ ] 1.1.2 关键点：独立组件（不复用 SkillCard），确保互斥展示（决策 D6）

### 1.2 渲染
- [ ] 1.2.1 顶层 `<div className="skill-info-banner" onClick={onClick}>`
- [ ] 1.2.2 显示 `🎯 已匹配 Skill: {skill_name}` 标题
- [ ] 1.2.3 显示 category badge：`<span className="skill-category-badge">{category === 'preset' ? '预设' : '自定义'}</span>`
- [ ] 1.2.4 工具 chips 渲染：前 3 个 + `+N more`
- [ ] 1.2.5 每个 chip 格式：`<span className="skill-tool-chip">🔧 {tool}</span>`

### 1.3 工具 chip 截断
- [ ] 1.3.1 `const visibleTools = tools?.slice(0, 3) || [];`
- [ ] 1.3.2 `const remaining = (tools?.length || 0) - 3;`
- [ ] 1.3.3 `remaining > 0` 时追加 `<span className="skill-tool-chip-more">+{remaining} more</span>`

### 1.4 单元测试
- [ ] 1.4.1 渲染最小 props 显示 skill 名称 + category
- [ ] 1.4.2 2 个 tools 显示 2 个 chips
- [ ] 1.4.3 5 个 tools 显示 3 个 chips + "+2 more"
- [ ] 1.4.4 点击触发 onClick 回调

---

## 2. `frontend/src/ChatPage.jsx` — 注册 onSkillMatched 回调

### 2.1 回调函数
- [ ] 2.1.1 在 `handleStreamSend` 的 `callbacks` 中新增 `onSkillMatched: (data) => { ... }`
- [ ] 2.1.2 回调体：更新 `message.skillMatched = {name, category, tools, correlation_id}`
- [ ] 2.1.3 关键点（设计 D10）：message 字段可选，不影响非 Skill 场景

### 2.2 状态机
- [ ] 2.2.1 同一 message 的 skillMatched 与 skillNeedMoreInfo 互斥（后到者覆盖前者）
- [ ] 2.2.2 同理 skillMatched 与 skillFailed 互斥
- [ ] 2.2.3 状态转换通过清空对方字段实现

---

## 3. `frontend/src/StreamingMessage.jsx` — 集成 SkillInfoBanner

### 3.1 在消息体顶部插入
- [ ] 3.1.1 条件渲染 `{message.skillMatched && <SkillInfoBanner ... />}` 在 message-content 之上
- [ ] 3.1.2 关键点（决策 D6）：与 need_more_info banner / failure banner 互斥
- [ ] 3.1.3 互斥逻辑：优先级 failure > need_more_info > info

### 3.2 互斥渲染
- [ ] 3.2.1 优先渲染 `message.skillFailed`（如有）→ 红色横幅
- [ ] 3.2.2 否则渲染 `message.skillNeedMoreInfo`（如有）→ 蓝色横幅
- [ ] 3.2.3 否则渲染 `message.skillMatched`（如有）→ 紫色 banner

---

## 4. `frontend/src/App.css` 样式

### 4.1 .skill-info-banner 基础
- [ ] 4.1.1 `.skill-info-banner { background: linear-gradient(135deg, #ede9fe 0%, #f3e8ff 100%); padding: 8px 12px; border-radius: 6px; border-bottom: 1px solid #c4b5fd; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; cursor: pointer; }`
- [ ] 4.1.2 `.skill-info-banner:hover { background: linear-gradient(135deg, #ddd6fe 0%, #ede9fe 100%); }`

### 4.2 工具 chip 样式
- [ ] 4.2.1 `.skill-tool-chip { font-family: monospace; font-size: 11px; padding: 2px 6px; background: rgba(255,255,255,0.6); border-radius: 3px; color: #4b5563; }`
- [ ] 4.2.2 `.skill-tool-chip-more { font-size: 11px; color: #6b7280; padding: 2px 4px; }`
