# Tasks: skill-failure-handling

> 对应 spec: [skill-failure-handling](../specs/skill-failure-handling/spec.md)
> 覆盖原 tasks.md 组 12（错误码）+ 组 14（agent Phase 2 失败/need_more_info 分支）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/errors.py` | 修改 | +15 | `skill_execution_failed` 工厂函数 + 错误码 |
| `app/agent.py` | 修改 | +30 | 三分支路由：success / need_approval / need_more_info / failure |

---

## 1. `app/errors.py` — 错误码定义

### 1.1 工厂函数
- [ ] 1.1.1 新增 `def skill_execution_failed(skill_name: str, error_detail: str) -> AgentError:`
- [ ] 1.1.2 截断逻辑：`error_detail = error_detail[:200] + "..." if len(error_detail) > 200 else error_detail`
- [ ] 1.1.3 构造 `AgentError(code="SKILL_EXECUTION_FAILED", message=f"技能 {skill_name} 执行失败：{error_detail}", source="skill", recoverable=True)`

### 1.2 关键约束（决策 5）
- [ ] 1.2.1 `recoverable=True` — 用户可重试或换说法
- [ ] 1.2.2 `source="skill"` — 区分于 `tool` / `llm` / `data`
- [ ] 1.2.3 错误消息含 skill 名称便于前端展示

### 1.3 单元测试
- [ ] 1.3.1 短错误（<200 字符）→ 完整 message
- [ ] 1.3.2 长错误（>200 字符）→ 截断带 `...`
- [ ] 1.3.3 `error.to_dict()` 返回 `{code, message, recoverable: true}`

---

## 2. `app/agent.py` — 三分支路由

### 2.1 chat() 路径
- [ ] 2.1.1 在 `chat()` 中，当 `matched_skill` 存在时调 `executor.execute(matched_skill, message, context, available_tools)` 得到 `workflow_result`
- [ ] 2.1.2 关键决策（决策 5 + 6）：**不**调 `_force_tool_retry` / `detect_tool_intent`
- [ ] 2.1.3 四分支判断：
  - `workflow_result is None` → 无工作流，注入 fragment 后让 LLM 自由调度
  - `workflow_result.success and not need_* ` → 成功，把 `intermediate_data` 作为 tool_calls 上下文，调 LLM 生成回复
  - `workflow_result.success and need_approval` → `_handle_skill_approval(workflow_result, messages, logger)`（见 skill-approval-bridge）
  - `workflow_result.success and need_more_info` → 注入 `intermediate_data` 到 system prompt，调 LLM（**不**传 tools）
  - `not workflow_result.success` → `build_error_response(skill_execution_failed(skill_name, workflow_result.error))`

### 2.2 need_more_info 注入
- [ ] 2.2.1 实现 `def _format_intermediate_for_llm(intermediate_data: dict) -> str:`
- [ ] 2.2.2 序列化为 JSON：`json.dumps(intermediate_data, ensure_ascii=False)`
- [ ] 2.2.3 截断：`content = content[:2000] if len(content) > 2000 else content`
- [ ] 2.2.4 截断时追加 `"...（数据过长，已省略）"`
- [ ] 2.2.5 构造 system message：
  ```python
  messages.append({
      "role": "system",
      "content": f"Skill '{skill.name}' 已执行部分步骤，当前状态：\n{content}\n请基于以上信息继续与用户对话以补充必要信息。"
  })
  ```
- [ ] 2.2.6 调 `call_llm(messages, tools=None)`（**不**传 tools，避免 LLM 误调工具）
- [ ] 2.2.7 返回 `{"reply": _strip_think_tags(response["content"]), "tool_calls": [], "pending_action": None, "error": None}`

### 2.3 失败兜底（决策 5）
- [ ] 2.3.1 当 `workflow_result.success = False`：
  - ❌ **不**调 `detect_tool_intent`
  - ❌ **不**调 `_force_tool_retry`
  - ❌ **不**创建 `pending_action`
  - ✅ 直接 `build_error_response(skill_execution_failed(...))`
- [ ] 2.3.2 关键点：失败是终态，明确报错给用户

### 2.4 stream_chat() 路径
- [ ] 2.4.1 同样三分支：failure → emit `done` with `error`
- [ ] 2.4.2 need_approval → emit `tool_call` + `done` with `pending_action`
- [ ] 2.4.3 need_more_info → emit `reply_chunk` for LLM response
- [ ] 2.4.4 success → emit `tool_result` + `done`

### 2.5 单元测试
- [ ] 2.5.1 Mock executor 返回 `success=False, error="..."` → 验证返回 `SKILL_EXECUTION_FAILED`
- [ ] 2.5.2 Mock executor 返回 `need_more_info=True, intermediate_data={...}` → 验证 messages 追加 system message 且不传 tools
- [ ] 2.5.3 验证 `intermediate_data` 序列化 > 2000 字符时被截断
- [ ] 2.5.4 验证失败路径不调 `detect_tool_intent`（grep 验证）
- [ ] 2.5.5 验证 need_more_info 路径不调工具

---

## 3. 端到端验证

- [ ] 3.1 发送触发 handler 异常的消息 → 响应含 `{error: {code: "SKILL_EXECUTION_FAILED", recoverable: true}}`
- [ ] 3.2 发送 "把订单 ORD-001 收货地址改了"（缺新地址）→ LLM 追问"请告诉我要改成什么？"
- [ ] 3.3 验证会话下次 chat 重新走 Skill 匹配（无粘性状态）
