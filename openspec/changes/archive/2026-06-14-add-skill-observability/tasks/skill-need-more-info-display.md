# Tasks: skill-need-more-info-display

> 对应 spec: [skill-need-more-info-display](../specs/skill-need-more-info-display/spec.md)
> 实施阶段: Phase 3（失败/need_more_info 标识）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `frontend/src/ChatPage.jsx` | 修改 | +~25 | 注册 onSkillNeedMoreInfo 回调 + 状态机 |
| `frontend/src/SkillCard.jsx` | 修改 | +~10 | 暂停态视觉（⏸️ 等待您回复） |
| `frontend/src/ChatPage.jsx` | 修改 | +~5 | 输入区 hint 提示 |
| `frontend/src/App.css` | 修改 | +~20 | `.skill-need-more-info-banner` 蓝色样式 |

---

## 1. `frontend/src/ChatPage.jsx` — onSkillNeedMoreInfo 回调

### 1.1 回调函数
- [ ] 1.1.1 在 `handleStreamSend` 的 `callbacks` 中新增 `onSkillNeedMoreInfo: (data) => { ... }`
- [ ] 1.1.2 回调体：填充 `message.skillNeedMoreInfo = {name, prompt, correlation_id}`
- [ ] 1.1.3 关键点（设计 D6）：独立字段，不与 skillMatched 合并

### 1.2 状态机（与 skillMatched / skillFailed 三态互斥）
- [ ] 1.2.1 need_more_info 触发时：保留 skillMatched（历史），新增 skillNeedMoreInfo 字段
- [ ] 1.2.2 不清空 skillMatched：用户能看到 SkillCard 折叠历史 + 蓝色追问标识
- [ ] 1.2.3 priority（前端渲染）：failure > need_more_info > info

### 1.3 输入区 hint
- [ ] 1.3.1 `const hasPendingSkillQuestion = activeSession?.messages?.some(m => m.skillNeedMoreInfo);`
- [ ] 1.3.2 在 input-hint 旁显示："💬 请回复 Skill 追问"
- [ ] 1.3.3 input 框 placeholder 切换："请回复 Skill 追问"
- [ ] 1.3.4 用户提交后，下一条 message 触发新的 skill 匹配，清除 hint

---

## 2. `frontend/src/SkillCard.jsx` — 暂停态视觉

### 2.1 Header 暂停徽章
- [ ] 2.1.1 当 `message.skillNeedMoreInfo` 存在时，header 显示 `⏸️ 等待您回复` 徽章
- [ ] 2.1.2 关键点（设计 D5/D6）：暂停态与折叠态正交——既可暂停又可折叠

### 2.2 步骤列表的"下一未执行"步骤
- [ ] 2.2.1 计算 `next_step` = 第一个 `status !== 'completed'` 且 `!== 'failed'` 的步骤
- [ ] 2.2.2 若 `next_step` 存在且 `skillNeedMoreInfo` 存在：渲染该步骤为虚线边框 + ⏸️ 图标
- [ ] 2.2.3 视觉提示用户"等待您补充输入后继续"

---

## 3. `frontend/src/App.css` 样式

### 3.1 .skill-need-more-info-banner
- [ ] 3.1.1 `.skill-need-more-info-banner { background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%); padding: 8px 12px; border-radius: 6px; border-bottom: 1px solid #93c5fd; color: #1e40af; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }`
- [ ] 3.1.2 `.skill-need-more-info-icon { font-size: 18px; }`
- [ ] 3.1.3 关键点：蓝色（区别于紫色 info 和红色 failure）
