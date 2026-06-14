# Tasks: skill-correlation-id

> 对应 spec: [skill-correlation-id](../specs/skill-correlation-id/spec.md)
> 实施阶段: Phase 1（与 skill-sse-events 一同实现，observability 助手类内部生成）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/observability.py` | 修改 | +~5 | `__init__` 生成 `self.correlation_id` |
| `app/agent.py` | 修改 | +~3 | 透传 correlation_id 到 message 字段 |
| `frontend/src/SkillCard.jsx` | 修改 | +~5 | footer 显示 correlation_id |
| `frontend/src/ChatPage.jsx` | 修改 | +~3 | message.correlationId 字段 |

---

## 1. `app/skills/observability.py` — correlation_id 生成

### 1.1 生成逻辑
- [ ] 1.1.1 在 `SkillObservability.__init__` 中：`self.correlation_id = f"skill_exec_{uuid.uuid4().hex[:12]}"`
- [ ] 1.1.2 关键点（设计 D2）：12 hex 字符足够唯一（48 位熵），紧凑可读
- [ ] 1.1.3 验证格式：`re.match(r"^skill_exec_[0-9a-f]{12}$", self.correlation_id)` 通过

### 1.2 注入到所有事件
- [ ] 1.2.1 5 个方法（skill_matched / workflow_step / workflow_result / skill_failed）的 emit payload 均含 `correlation_id: self.correlation_id`
- [ ] 1.2.2 关键点：所有 emit 使用同一 ID，确保跨事件可关联

---

## 2. `app/agent.py` — 透传

### 2.1 chat() 透传
- [ ] 2.1.1 SkillObservability 实例的 correlation_id 注入 chat_response（未来 SSE 事件已含）
- [ ] 2.1.2 当 chat 同步响应包含 Skill 数据时（如 workflow_result），response 增加 `skill_correlation_id` 字段

---

## 3. `frontend/src/ChatPage.jsx` — message 字段

### 3.1 correlationId 字段
- [ ] 3.1.1 新增 `message.correlationId` 字段（onSkillMatched 回调时填入 `data.correlation_id`）
- [ ] 3.1.2 关键点（设计 D10）：与 skillMatched / workflowSteps / skillFailed 同级字段

### 3.2 透传到 SkillCard
- [ ] 3.2.1 `<SkillCard correlation_id={message.correlationId} ... />`
- [ ] 3.2.2 关键点：单一来源（message.correlationId），所有展示组件读取同一字段

---

## 4. `frontend/src/SkillCard.jsx` — Footer 展示

### 4.1 correlation_id 渲染
- [ ] 4.1.1 `{correlation_id && <div className="skill-correlation-id" title="Skill 执行追踪 ID，可在日志中按此 ID 检索完整事件链">🔗 {correlation_id}</div>}`
- [ ] 4.1.2 关键点：默认折叠时不显示（避免视觉杂乱）；展开后才显示

---

## 5. 单测

### 5.1 后端单测
- [ ] 5.1.1 测试 correlation_id 格式 `^skill_exec_[0-9a-f]{12}$`
- [ ] 5.1.2 测试 100 次生成无重复
- [ ] 5.1.3 测试 5 个方法 emit 携带同一 correlation_id

### 5.2 前端单测
- [ ] 5.2.1 SkillCard 接收 correlation_id="skill_exec_abc123" 显示在 footer
- [ ] 5.2.2 SkillCard 不传 correlation_id 不显示 footer
- [ ] 5.2.3 折叠态不显示 footer（展开时才显示）
