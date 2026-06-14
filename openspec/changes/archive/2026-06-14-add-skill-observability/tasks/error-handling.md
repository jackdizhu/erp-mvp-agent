# Tasks: error-handling (modified)

> 对应 spec: [error-handling](../specs/error-handling/spec.md)（delta — ADDED）
> 实施阶段: Phase 1（与 skill-failure-rendering 配套）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/ChatPage.jsx` | 修改 | +~15 | SSE `error` 事件中识别 SKILL_EXECUTION_FAILED 码 + 渲染红色横幅 |
| `frontend/src/StreamingMessage.jsx` | 修改 | +~15 | 复用 `.error-message-banner` CSS 渲染 SKILL_EXECUTION_FAILED 错误 |

---

## 1. `frontend/src/ChatPage.jsx` — 错误识别

### 1.1 错误码分支
- [ ] 1.1.1 在 `onError` 回调中识别 `err.code === "SKILL_EXECUTION_FAILED"` 走 Skill 错误路径
- [ ] 1.1.2 关键点：与现有 MCP 错误码分支共存（spec 6-4-1 in error-handling spec）

### 1.2 错误消息截断
- [ ] 1.2.1 显示 `err.message`（agent.py: skill_execution_failed 工厂已截断 200 字符）
- [ ] 1.2.2 追加 `（错误码：${err.code}）` 到消息末尾
- [ ] 1.2.3 追加 `（可重试或换种方式描述）` 当 `err.recoverable !== false`

### 1.3 message 字段填充
- [ ] 1.3.1 `msg.skillFailed = {name: <last_matched_skill>, error_code: err.code, error_detail: err.message, correlation_id: <last_correlation_id>}`
- [ ] 1.3.2 关键点：correlation_id 需在 Skill 命中时缓存，失败时携带

---

## 2. `frontend/src/StreamingMessage.jsx` — 错误横幅

### 2.1 复用 error-message-banner
- [ ] 2.1.1 渲染 `<div className="error-message-banner"><span className="error-icon">⚠️</span><span className="error-text">{message.skillFailed.error_detail}</span></div>`
- [ ] 2.1.2 关键点：复用现有 CSS 类（不需新增样式）
- [ ] 2.1.3 添加 hint 文本：`<span className="error-hint">（错误码：${error_code}）可重试或换种方式描述</span>`

### 2.2 与 SkillCard 共存
- [ ] 2.2.1 错误横幅在 SkillCard 之上（先显示）
- [ ] 2.2.2 SkillCard 可展开查看失败步骤
- [ ] 2.2.3 关键点：失败时 SkillCard 仍展示历史（让用户看到执行到哪步失败）

### 2.3 单元测试
- [ ] 2.3.1 渲染带 skillFailed 的 message：error banner 可见
- [ ] 2.3.2 验证 hint 文本（错误码 + 可重试）渲染正确
