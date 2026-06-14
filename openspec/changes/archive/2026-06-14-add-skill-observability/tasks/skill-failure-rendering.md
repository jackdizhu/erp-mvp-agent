# Tasks: skill-failure-rendering

> 对应 spec: [skill-failure-rendering](../specs/skill-failure-rendering/spec.md)
> 实施阶段: Phase 3（失败/need_more_info 标识）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/ChatPage.jsx` | 修改 | +~20 | 注册 onSkillFailed 回调 + 填充 message.skillFailed + 清空 skillMatched |
| `frontend/src/StreamingMessage.jsx` | 修改 | +~20 | 失败横幅渲染（复用 .error-message-banner） + 与 SkillCard 互斥 |
| `frontend/src/SkillCard.jsx` | 修改 | +~10 | 接收 failed_step_id props + 高亮失败行 |

---

## 1. `frontend/src/ChatPage.jsx` — onSkillFailed 回调

### 1.1 回调函数
- [ ] 1.1.1 在 `handleStreamSend` 的 `callbacks` 中新增 `onSkillFailed: (data) => { ... }`
- [ ] 1.1.2 回调体：填充 `message.skillFailed = {name, error_code, error_detail, failed_step_id, correlation_id}`
- [ ] 1.1.3 关键点：清空 `message.skillMatched`（失败时不再显示命中 banner）

### 1.2 状态机
- [ ] 1.2.1 skillFailed 覆盖 skillMatched（互斥）：失败时后者保留供 SkillCard 展示步骤历史，前者清空
- [ ] 1.2.2 实际：保留 skillMatched（SkillCard 仍展示）+ 新增 skillFailed（红色横幅）
- [ ] 1.2.3 关键点：横幅和 Card 共存（用户能看到 SkillCard 折叠历史 + 失败原因）

### 1.3 错误码透传
- [ ] 1.3.1 `error_code` 默认为 "SKILL_EXECUTION_FAILED"
- [ ] 1.3.2 `error_detail` 截断 100 字符（前端显示用）
