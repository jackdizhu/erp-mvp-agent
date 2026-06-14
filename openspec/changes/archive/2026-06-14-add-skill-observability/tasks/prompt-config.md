# Tasks: prompt-config (modified)

> 对应 spec: [prompt-config](../specs/prompt-config/spec.md)（delta — ADDED）
> 实施阶段: Phase 1

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/agent.py` | 修改 | +~5 | chat() 调 build_system_prompt 后记录 skill_fragment_applied 日志 |
| `app/agent_logger.py` | 修改 | +~10 | 新增 `log_skill_fragment_applied` 方法 |

---

## 1. `app/agent_logger.py` — log_skill_fragment_applied 方法

### 1.1 方法定义
- [ ] 1.1.1 实现 `def log_skill_fragment_applied(self, fragment_preview: str, fragment_length: int) -> None:`
- [ ] 1.1.2 data 字段：`{fragment_preview, fragment_length, applied_at: timestamp}`（applied_at 可选，timestamp 已自动加）
- [ ] 1.1.3 调 `self._write("skill_fragment_applied", data)`

### 1.2 截断
- [ ] 1.2.1 fragment_preview 截断 200 字符（与 design D7 一致）

---

## 2. `app/agent.py` — 调用

### 2.1 在 build_messages 之后
- [ ] 2.1.1 chat() 中：`messages = build_messages(message, history, skill_fragments=skill_fragments)`
- [ ] 2.1.2 若 `skill_fragments and logger:` `logger.log_skill_fragment_applied(skill_fragments[:200], len(skill_fragments))`
- [ ] 2.1.3 关键点：仅当 fragments 非空时记日志（避免冗余）

### 2.2 单元测试
- [ ] 2.2.1 Mock logger，验证 build_system_prompt 注入片段后调 log_skill_fragment_applied
- [ ] 2.2.2 验证空 fragments 不调
