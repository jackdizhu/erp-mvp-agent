# Tasks: skill-sse-events

> 对应 spec: [skill-sse-events](../specs/skill-sse-events/spec.md)
> 实施阶段: Phase 1（后端 SSE + 日志）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/observability.py` | 新建 | ~120 | `SkillObservability` 助手类（封装 SSE + 日志 + correlation_id） |
| `app/agent.py` | 修改 | +~40 | 在 chat() Skill 路径 4 分支调 `SkillObservability` |
| `app/main.py` | 修改 | +~10 | 注入 `on_event` 到 `SkillObservability`（stream_chat 路径） |

---

## 1. `app/skills/observability.py` — SkillObservability 助手类

### 1.1 类结构
- [ ] 1.1.1 定义 `class SkillObservability:` 接收 `logger: SessionLogger`, `on_event: Callable[[str, dict], None]`, `skill: SkillConfig`
- [ ] 1.1.2 `__init__` 生成 `self.correlation_id = f"skill_exec_{uuid.uuid4().hex[:12]}"`
- [ ] 1.1.3 存储 `self.skill_name = skill.name` / `self.category = skill.category` / `self.has_workflow = skill.workflow is not None` / `self.has_handler = skill.has_handler()`
- [ ] 1.1.4 关键点（设计 D1）：`on_event` 与 `logger` 注入，单一实例持整个执行生命周期的 correlation_id

### 1.2 skill_matched 方法
- [ ] 1.2.1 实现 `def skill_matched(self) -> None:`
- [ ] 1.2.2 emit `event: skill_matched` 携带 `{name, category, description, tools, has_workflow, has_handler, correlation_id}`
- [ ] 1.2.3 调 `logger.log_skill_matched(skill_name, category, has_workflow, has_handler, correlation_id, prompt_fragment)`
- [ ] 1.2.4 try/except 包裹 emit + log，失败不中断主流程

### 1.3 workflow_step 方法
- [ ] 1.3.1 实现 `def workflow_step(self, step_id: str, type: str, status: str, tool: Optional[str]=None, instruction: Optional[str]=None, elapsed_ms: Optional[int]=None, result_summary: Optional[str]=None) -> None:`
- [ ] 1.3.2 emit `event: workflow_step` 携带 `{correlation_id, step_id, type, tool?, instruction?, status, elapsed_ms?, result_summary?}`
- [ ] 1.3.3 调 `logger.log_workflow_step(correlation_id, skill_name, step_id, type, status, tool, instruction, result, error)`
- [ ] 1.3.4 关键点（设计 D4）：仅完成/失败时调，pending 态不调

### 1.4 workflow_result 方法
- [ ] 1.4.1 实现 `def workflow_result(self, success: bool, need_approval: bool, need_more_info: bool, step_count: int) -> None:`
- [ ] 1.4.2 emit `event: workflow_result` 携带 `{correlation_id, success, need_approval, need_more_info, step_count}`
- [ ] 1.4.3 调 `logger.log_workflow_result(correlation_id, skill_name, success, need_approval, need_more_info, step_count)`

### 1.5 skill_failed 方法
- [ ] 1.5.1 实现 `def skill_failed(self, error_code: str, error_detail: str, failed_step_id: Optional[str]=None) -> None:`
- [ ] 1.5.2 emit `event: skill_failed` 携带 `{correlation_id, name, error_code, error_detail, failed_step_id?}`
- [ ] 1.5.3 调 `logger.log_skill_failed(correlation_id, skill_name, error_code, error_detail, failed_step_id)`

### 1.6 单元测试（单文件 ≤ 1 小时）
- [ ] 1.6.1 测试 correlation_id 格式 `^skill_exec_[0-9a-f]{12}$`
- [ ] 1.6.2 测试 5 个方法 emit + log 各 1 次（用 mock SessionLogger + mock on_event）
- [ ] 1.6.3 测试 emit 异常时 log 仍执行（解耦）
- [ ] 1.6.4 测试 100 次生成无重复 correlation_id

---

## 2. `app/agent.py` 修改 — 集成 SkillObservability

### 2.1 chat() 路径集成
- [ ] 2.1.1 导入 `from app.skills.observability import SkillObservability`
- [ ] 2.1.2 在 chat() 顶部（Skill 命中后）创建 `obs = SkillObservability(logger=logger, on_event=on_event, skill=matched_skill)`（注：on_event 需通过参数传入或 module-level）
- [ ] 2.1.3 关键点（设计 D1）：on_event 注入方式 — 优先通过参数传入；如 chat() 不接受 on_event 参数，则在 main.py 层封装 emit 函数
- [ ] 2.1.4 调用 `obs.skill_matched()` 在 `matched_skill` 确认后、executor.execute() 之前
- [ ] 2.1.5 4 个分支 emit：
  - need_approval → `obs.workflow_result(success=True, need_approval=True, need_more_info=False, step_count=...)`
  - need_more_info → `obs.workflow_result(success=True, need_approval=False, need_more_info=True, step_count=...)`
  - 成功（无 flags）→ `obs.workflow_result(success=True, need_approval=False, need_more_info=False, step_count=...)`
  - 失败 → `obs.skill_failed("SKILL_EXECUTION_FAILED", workflow_result.error, failed_step_id=...)`

### 2.2 workflow_step emit（来自 executor 回调）
- [ ] 2.2.1 在 chat() 中创建 `on_step_complete = lambda step_def, status, result, error, elapsed_ms: obs.workflow_step(...)`
- [ ] 2.2.2 调 `executor.execute(skill, message, context, available_tools, on_step_complete=on_step_complete)`
- [ ] 2.2.3 关键点（设计 D9）：executor 通过回调通知，避免 executor 耦合 SSE 副作用

### 2.3 executor.py 修改（配套）
- [ ] 2.3.1 `def execute(self, skill, message, context, available_tools=None, on_step_complete: Optional[Callable]=None) -> Optional[WorkflowResult]:`
- [ ] 2.3.2 `_execute_yaml_workflow` 接受 `on_step_complete` 参数
- [ ] 2.3.3 每完成一 `tool_call` 步骤，调 `on_step_complete(step_def, status='completed', result=..., error=None, elapsed_ms=...)`
- [ ] 2.4.4 每完成一 `prompt` 步骤，调 `on_step_complete(step_def, status='completed', result=None, error=None, elapsed_ms=...)`
- [ ] 2.3.5 步骤失败时调 `on_step_complete(step_def, status='failed', result=None, error=str(e), elapsed_ms=...)`
- [ ] 2.3.6 计算 elapsed_ms：`time.monotonic() - start_time` 转换为 int 毫秒
- [ ] 2.3.7 on_step_complete 为 None 时跳过（保持向后兼容）

### 2.4 单元测试
- [ ] 2.4.1 Mock SkillObservability，验证 chat() Skill 路径调用顺序：skill_matched → workflow_step(N) → workflow_result
- [ ] 2.4.2 验证失败路径调用 skill_failed 而非 workflow_result
- [ ] 2.4.3 验证 emit 异常被 try/except 捕获不影响主流程

---

## 3. `app/main.py` 修改 — 注入 on_event

### 3.1 封装 emit 函数
- [ ] 3.1.1 在 `chat_endpoint` 中创建 `def emit(event_type, data): q.put(format_sse_event(event_type, data))`
- [ ] 3.1.2 在 chat() 调用前通过某种机制传 on_event 给 chat()（或 module-level 注入）
- [ ] 3.1.3 关键点：避免修改 chat() 函数签名（向后兼容）

### 3.2 临时方案：用 contextvars（推荐）
- [ ] 3.2.1 引入 `from contextvars import ContextVar`
- [ ] 3.2.2 定义 `current_on_event: ContextVar[Optional[Callable]] = ContextVar("current_on_event", default=None)`
- [ ] 3.2.3 在 chat_endpoint 中 `token = current_on_event.set(emit)`，`chat(...)`，`current_on_event.reset(token)`
- [ ] 3.2.4 在 agent.py 中 `on_event = current_on_event.get()` 获取
- [ ] 3.2.5 传给 SkillObservability 构造

### 3.3 单元测试
- [ ] 3.3.1 验证 current_on_event 未设置时 chat() 不报错（on_event 为 None，SkillObservability 跳过 emit）
- [ ] 3.3.2 验证 contextvars 在并发请求间隔离
