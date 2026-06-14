# Tasks: error-handling (modified)

> 对应 spec: [error-handling](../specs/error-handling/spec.md)（delta — ADDED SKILL_EXECUTION_FAILED）
> 覆盖原 tasks.md 组 12（错误码定义）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/errors.py` | 修改 | +15 | 新增 `skill_execution_failed` 工厂函数 |

---

## 1. 错误码常量

### 1.1 命名约定
- [ ] 1.1.1 错误码 `SKILL_EXECUTION_FAILED` 沿用 `SKILL_` 前缀（与 `TOOL_` / `DATA_` / `APPROVAL_` / `LLM_` / `SYS_` 保持一致）
- [ ] 1.1.2 `source="skill"` 区分于 `tool` / `llm` / `data` / `approval` / `system`

---

## 2. 工厂函数

### 2.1 实现
- [ ] 2.1.1 在 `app/errors.py` 末尾新增：
  ```python
  def skill_execution_failed(skill_name: str, error_detail: str) -> AgentError:
      truncated = error_detail[:200] + "..." if len(error_detail) > 200 else error_detail
      return AgentError(
          code="SKILL_EXECUTION_FAILED",
          message=f"技能 {skill_name} 执行失败：{truncated}",
          source="skill",
          recoverable=True
      )
  ```
- [ ] 2.1.2 关键点：`recoverable=True` — 用户可换说法或重试

### 2.2 单元测试
- [ ] 2.2.1 短错误（<200 字符）→ message 完整保留
- [ ] 2.2.2 长错误（>200 字符）→ 截断为前 200 字符 + `...`
- [ ] 2.2.3 边界：200 字符不截断；201 字符截断
- [ ] 2.2.4 `to_dict()` 返回 `{code, message, recoverable: true}`

---

## 3. 使用点（agent.py 集成）

### 3.1 chat() 失败分支
- [ ] 3.1.1 `app/agent.py` 中 Skill 命中但 `workflow_result.success=False` 时调 `build_error_response(skill_execution_failed(matched_skill.name, workflow_result.error))`
- [ ] 3.1.2 关键决策（决策 5）：**不**调用 `_force_tool_retry`，直接返回错误

### 3.2 stream_chat() 失败分支
- [ ] 3.2.1 emit `done` 事件携带 `{complete: False, error: skill_execution_failed(...).to_dict()}`

### 3.3 端到端验证
- [ ] 3.3.1 触发 handler 异常 → 响应 `{reply: "技能 query-order-search 执行失败：...", error: {code: "SKILL_EXECUTION_FAILED", recoverable: true}}`
- [ ] 3.3.2 触发 YAML step 异常 → 响应 message 含 `"步骤 'X' 执行失败: ..."`

---

## 4. 错误码参考表更新

- [ ] 4.1 在 `app/errors.py` 顶部注释（如果有）更新错误码列表，新增 `SKILL_EXECUTION_FAILED`
- [ ] 4.2 在 `docs/architecture.md` 错误码章节同步（如有）
