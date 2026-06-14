# Tasks: agent-core (modified)

> 对应 spec: [agent-core](../specs/agent-core/spec.md)（delta — ADDED）
> 实施阶段: Phase 1 + Phase 2
> 覆盖：Skill 路径 emit 新 SSE 事件 + SkillObservability 集成

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/agent.py` | 修改 | +~80 | chat() Skill 路径 4 分支 emit + 回调注册 |
| `app/main.py` | 修改 | +~15 | 注入 emit 函数 + 包装 SkillObservability 上下文 |

详见 [skill-sse-events](skill-sse-events.md) 第 2-3 节的细化任务。

---

## 1. `app/agent.py` — chat() 路径集成

### 1.1 import
- [ ] 1.1.1 添加 `from app.skills.observability import SkillObservability`
- [ ] 1.1.2 添加 `from contextvars import ContextVar`
- [ ] 1.1.3 定义 `current_on_event: ContextVar[Optional[Callable]] = ContextVar("current_on_event", default=None)`

### 1.2 入口 emit
- [ ] 1.2.1 在 chat() 顶部（Skill 命中后）创建 `obs = SkillObservability(logger=logger, on_event=current_on_event.get(), skill=matched_skill)`
- [ ] 1.2.2 调 `obs.skill_matched()` 立即（确保前端即时收到 skill_matched 事件）

### 1.3 4 分支 emit（详见 skill-sse-events 任务 2.1.5）
- [ ] 1.3.1 need_approval → `obs.workflow_result(success=True, need_approval=True, need_more_info=False, step_count=...)`
- [ ] 1.3.2 need_more_info → `obs.workflow_result(success=True, need_approval=False, need_more_info=True, step_count=...)`
- [ ] 1.3.3 成功（无 flags）→ `obs.workflow_result(success=True, need_approval=False, need_more_info=False, step_count=...)`
- [ ] 1.3.4 失败 → `obs.skill_failed("SKILL_EXECUTION_FAILED", error_detail, failed_step_id=...)`

### 1.4 workflow_step 回调注册
- [ ] 1.4.1 创建 `on_step_complete = lambda step_def, status, result, error, elapsed_ms: obs.workflow_step(...)`
- [ ] 1.4.2 调 `executor.execute(skill, message, context, available_tools, on_step_complete=on_step_complete)`
- [ ] 1.4.3 关键点（设计 D9）：executor 通过回调通知，不耦合 SSE 副作用

### 1.5 stream_chat() 路径（Phase 3，预留）
- [ ] 1.5.1 Phase 3 范围：stream_chat() 同样集成 SkillObservability
- [ ] 1.5.2 当前 Phase 1 仅实现 chat() 路径，stream_chat() 标记 TODO

---

## 2. `app/main.py` — emit 注入

### 2.1 emit 函数封装
- [ ] 2.1.1 在 `chat_endpoint` 异步函数中定义 `def emit(event_type, data): await queue.put(format_sse_event(event_type, data))`
- [ ] 2.1.2 注：SSE emit 是异步的，chat() 内部 emit 需通过 contextvar + asyncio.Queue

### 2.2 contextvar 注入
- [ ] 2.2.1 `token = current_on_event.set(emit)`
- [ ] 2.2.2 `try: result = chat(...) finally: current_on_event.reset(token)`
- [ ] 2.2.3 关键点：contextvar 跨 await 边界传递，chat() 内部通过 `current_on_event.get()` 获取

### 2.3 单元测试
- [ ] 2.3.1 测试 contextvar 注入 + 重置（多请求隔离）
- [ ] 2.3.2 测试未注入时 chat() 不报错（on_event 为 None，SkillObservability 跳过）
