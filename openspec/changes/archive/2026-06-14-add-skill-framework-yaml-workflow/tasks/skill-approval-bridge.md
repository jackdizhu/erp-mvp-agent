# Tasks: skill-approval-bridge

> 对应 spec: [skill-approval-bridge](../specs/skill-approval-bridge/spec.md)
> 覆盖原 tasks.md 组 13（审批桥接函数）+ 组 7.3（handler 解耦约束）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/agent.py` | 修改 | +~50 | 新增 `_handle_skill_approval` 桥接函数 |
| `skills/query-order-edit-address/handler.py` | 新建 | ~110 | 解耦：handler **不** import `app.approval_core` |

---

## 1. 桥接契约（handler 实现约束）

### 1.1 handler.py 实现规范
- [ ] 1.1.1 `handler.py` 只 import：`from app.skills.base import SkillHandler, WorkflowStep, WorkflowResult` + `from app.clients.client_factory import client_factory` + 标准库
- [ ] 1.1.2 **禁止** import：`app.approval_core` / `app.agent` / `app.intent_detector`
- [ ] 1.1.3 关键点：handler 通过 `intermediate_data` 字典传递意图，**不**直接调用副作用

### 1.2 审批契约字段
- [ ] 1.2.1 当 handler 决定需要审批时返回：`WorkflowResult(success=True, need_approval=True, intermediate_data={...})`
- [ ] 1.2.2 `intermediate_data` **必须**包含三个 key：
  - `tool: str` — 目标工具名（如 `update_order`）
  - `tool_args: dict` — 工具调用参数
  - `approval_summary: str` — 人类可读审批摘要
- [ ] 1.2.3 缺失任一 key → agent 返回 `SKILL_EXECUTION_FAILED`，不调 `approval_core`

### 1.3 handler 单测可行性
- [ ] 1.3.1 验证 handler.py 单测**不**需要 mock `approval_core`
- [ ] 1.3.2 验证 `from app.approval_core import` 出现在 handler.py 中时测试失败（linter rule 或 grep 检查）

---

## 2. `app/agent.py:_handle_skill_approval`

### 2.1 函数签名
- [ ] 2.1.1 定义 `def _handle_skill_approval(workflow_result: WorkflowResult, messages: list, logger=None) -> dict:`
- [ ] 2.1.2 位置：在 `_handle_tool_calls` 之后定义，便于复用

### 2.2 契约校验
- [ ] 2.2.1 从 `workflow_result.intermediate_data` 读 `tool` / `tool_args` / `approval_summary`
- [ ] 2.2.2 任意 key 缺失：`logger.error("Skill approval contract missing keys")` + `return build_error_response(skill_execution_failed(skill_name, "missing approval contract"))`
- [ ] 2.2.3 关键点：**不**调用 `detect_tool_intent`，直接报错

### 2.3 桥接到 approval_core
- [ ] 2.3.1 调 `approval_core.create_pending(tool, tool_args, messages)`
- [ ] 2.3.2 返回 None → `return build_error_response(approval_failed(tool))`
- [ ] 2.3.3 成功 → 构造返回 dict：
  ```python
  return {
      "reply": f"需要确认以下操作：{approval_summary}",
      "tool_calls": [{
          "tool": tool,
          "args": tool_args,
          "status": "pending_approval",
          "action_id": action["action_id"]
      }],
      "pending_action": action,
      "error": None
  }
  ```

### 2.4 桥接返回值与现有 DANGER 路径对齐
- [ ] 2.4.1 验证 `pending_action` 字段结构与 `agent.py:171-177` 现存 DANGER 分支返回一致
- [ ] 2.4.2 验证 `tool_calls[i].status = "pending_approval"` 与前端 ApprovalCard 期望一致
- [ ] 2.4.3 验证 `reply` 前缀 `"需要确认以下操作："` 与现有 `_handle_tool_calls:173` 一致

### 2.5 流式路径
- [ ] 2.5.1 在 `stream_chat` 中同样处理：emit `tool_call` 事件 → emit `done` 事件携带 `pending_action`
- [ ] 2.5.2 参考 `_handle_tool_calls_stream` 中 DANGER 分支的事件顺序

### 2.6 单元测试
- [ ] 2.6.1 Mock `approval_core.create_pending` 返回成功 → 验证返回结构
- [ ] 2.6.2 Mock `approval_core.create_pending` 返回 None → 验证返回 `approval_failed` 错误
- [ ] 2.6.3 `intermediate_data` 缺 `tool` → 验证返回 `SKILL_EXECUTION_FAILED`
- [ ] 2.6.4 验证不调 `detect_tool_intent`（grep 验证）
