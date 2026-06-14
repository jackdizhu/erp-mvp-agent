# Tasks: agent-core (modified)

> 对应 spec: [agent-core](../specs/agent-core/spec.md)（delta — ADDED）
> 覆盖原 tasks.md 组 9（Phase 1 集成）+ 组 14（Phase 2 启用）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/agent.py` | 修改 | +50 | `chat()` / `stream_chat()` / `build_messages()` 集成 Skill |
| `app/config.py` | 修改 | +3 | `ENABLE_SKILL` 标志（Phase 1 false / Phase 2 true） |

---

## 1. `app/config.py` — 新增标志

- [ ] 1.1 添加 `ENABLE_SKILL: bool = False`（Phase 1 默认 false，保持向后兼容）
- [ ] 1.2 添加注释说明 Phase 1 / Phase 2 切换
- [ ] 1.3 关键点：默认 false 时，未命中 Skill 的行为**字节级**与现状一致

---

## 2. `app/agent.py:build_messages` 改造

### 2.1 import 调整
- [ ] 2.1.1 删除 `from app.llm import ... SYSTEM_PROMPT`（决策 2）
- [ ] 2.1.2 添加 `from app.prompt_config import build_system_prompt`
- [ ] 2.1.3 添加 `from app.skills.registry import get_skill_registry`
- [ ] 2.1.4 添加 `from app.skills.executor import SkillExecutor`
- [ ] 2.1.5 添加 `from app.skills.base import WorkflowResult`
- [ ] 2.1.6 添加 `from app.errors import skill_execution_failed`

### 2.2 build_messages 签名
- [ ] 2.2.1 改 `def build_messages(message: str, history: list) -> list:` 为 `def build_messages(message: str, history: list, skill_fragments: str = "") -> list:`
- [ ] 2.2.2 删除 `from app.llm import SYSTEM_PROMPT` 的引用
- [ ] 2.2.3 改 `messages = [{"role": "system", "content": SYSTEM_PROMPT}]` 为：
  ```python
  system_prompt = build_system_prompt(skill_fragments)
  messages = [{"role": "system", "content": system_prompt}]
  ```

---

## 3. `app/agent.py:chat()` Skill 集成

### 3.1 Phase 1 路径（ENABLE_SKILL=False）
- [ ] 3.1.1 `chat()` 顶部保持不变，未命中 skill 时 `skill_fragments=""`
- [ ] 3.1.2 行为字节级与 Phase 0 一致

### 3.2 Phase 2 路径（ENABLE_SKILL=True）— Skill 优先
- [ ] 3.2.1 在 `chat()` 顶部添加：
  ```python
  matched_skill = None
  if ENABLE_SKILL:
      registry = get_skill_registry()
      if registry:
          matched_skill = registry.match_skill(message)
  ```
- [ ] 3.2.2 调 `build_messages(message, history, skill_fragments=matched_skill.prompt_fragment if matched_skill else "")`
- [ ] 3.2.3 关键决策（决策 3）：**命中 Skill 后跳过** `detect_tool_intent` 与 `_force_tool_retry`

### 3.3 Skill 命中时分支
- [ ] 3.3.1 命中后调 `executor = SkillExecutor()` → `workflow_result = executor.execute(matched_skill, message, context={"messages": messages, "client_factory": client_factory}, available_tools=[t["function"]["name"] for t in client_factory.get_all_tools()])`
- [ ] 3.3.2 四分支判断（详见 [skill-failure-handling](skill-failure-handling.md)）：
  - `success and not need_*` → 继续正常流，把 workflow_result.intermediate_data 注入
  - `need_approval` → `_handle_skill_approval(workflow_result, messages, logger)`
  - `need_more_info` → 注入 system message 后调 LLM
  - `not success` → `build_error_response(skill_execution_failed(matched_skill.name, workflow_result.error))`

### 3.4 未命中 Skill 兜底
- [ ] 3.4.1 `matched_skill is None` → 走原有 `detect_tool_intent` 流程（保留 `_force_tool_retry`）
- [ ] 3.4.2 关键点：兜底保留是为了不破坏"无 Skill 配置"环境的兼容性

---

## 4. `app/agent.py:stream_chat()` Skill 集成

### 4.1 入口改造
- [ ] 4.1.1 在 `stream_chat()` 顶部添加 `matched_skill` 解析（同 chat 逻辑）
- [ ] 4.1.2 调 `build_messages(message, history, skill_fragments=...)`

### 4.2 Skill 执行结果处理
- [ ] 4.2.1 `workflow_result is None` → 继续原有 LLM 自由调度
- [ ] 4.2.2 `need_approval` → emit `tool_call` + `done` with `pending_action`
- [ ] 4.2.3 `need_more_info` → emit `reply_chunk` 后 `done`
- [ ] 4.2.4 `success` → emit `tool_result` + `done`
- [ ] 4.2.5 `failure` → emit `done` with `error`

---

## 5. 端到端测试

- [ ] 5.1 ENABLE_SKILL=False 时，与 Phase 0 行为字节级一致（端到端对比 5 条典型消息）
- [ ] 5.2 ENABLE_SKILL=True + 命中 query-order-search → LLM 收到 fragment + 自由调 tool
- [ ] 5.3 ENABLE_SKILL=True + 命中 query-order-edit-address + 需要审批 → 返回 pending_action
- [ ] 5.4 ENABLE_SKILL=True + 命中 query-order-edit-address + need_more_info → LLM 追问
- [ ] 5.5 ENABLE_SKILL=True + 命中 skill 但 handler 异常 → 返回 SKILL_EXECUTION_FAILED（**不**兜底）
- [ ] 5.6 ENABLE_SKILL=True + 未命中 → 走 detect_tool_intent 原有路径

---

## 6. 互斥保证（grep 验证）

- [ ] 6.1 `grep -n "detect_tool_intent\|_force_tool_retry" app/agent.py` 在 Skill 命中分支**不**出现
- [ ] 6.2 验证 `agent.py` 中 `if matched_skill:` 分支**不**有 `detect_tool_intent(` 调用
