# Tasks: prompt-config (modified)

> 对应 spec: [prompt-config](../specs/prompt-config/spec.md)（delta — MODIFIED + ADDED）
> 覆盖原 tasks.md 组 8（prompt_config 改造）+ 组 9（agent 集成）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/prompt_config.py` | 修改 | +5 | `build_system_prompt` 新增 `skill_fragments` 参数 |

---

## 1. 函数签名变更

### 1.1 旧签名
- [ ] 1.1.1 当前 `def build_system_prompt() -> str:`（[app/prompt_config.py:32](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/app/prompt_config.py#L32)）

### 1.2 新签名
- [ ] 1.2.1 改为 `def build_system_prompt(skill_fragments: str = "") -> str:`
- [ ] 1.2.2 默认空串保证向后兼容（Phase 1 调用方无需改）

---

## 2. 注入逻辑

### 2.1 现有逻辑保留
- [ ] 2.1.1 保持 `role` / `capabilities_header` / `capabilities` / `risk_notice` / `response_style` 拼装顺序不变
- [ ] 2.1.2 保持 `parts` 列表追加模式

### 2.2 新增技能指引段落
- [ ] 2.2.1 在 `return "\n".join(parts)` 之前追加：
  ```python
  if skill_fragments:
      parts.append("")
      parts.append("=== 技能指引 ===")
      parts.append(skill_fragments)
  ```
- [ ] 2.2.2 关键点：空字符串不追加 section（避免冗余空行）
- [ ] 2.2.3 关键点：使用 `"\n".join(parts)` 时空字符串 parts 会产生空行——上面条件分支确保仅在非空时追加空串触发段落分隔

---

## 3. `__all__` 导出

- [ ] 3.1 保持 `__all__ = ["build_system_prompt", "build_capabilities_list"]`

---

## 4. 调用方更新（`app/agent.py`）

### 4.1 旧调用
- [ ] 4.1.1 当前 `app/llm.py:21` `SYSTEM_PROMPT = build_system_prompt()`（将被删除）
- [ ] 4.1.2 `app/agent.py:31` `messages = [{"role": "system", "content": SYSTEM_PROMPT}]`

### 4.2 新调用
- [ ] 4.2.1 `app/agent.py:build_messages` 内：
  ```python
  system_prompt = build_system_prompt(skill_fragments)
  messages = [{"role": "system", "content": system_prompt}]
  ```
- [ ] 4.2.2 删除 `app/llm.py:21` 的模块级 `SYSTEM_PROMPT`
- [ ] 4.2.3 删除 `app/agent.py:7` 的 `from app.llm import SYSTEM_PROMPT`

---

## 5. 单元测试

### 5.1 默认空调用（向后兼容）
- [ ] 5.1.1 `build_system_prompt()` 无参 → 输出不含 "=== 技能指引 ==="
- [ ] 5.1.2 与 Phase 0 输出**字节级**一致

### 5.2 非空片段
- [ ] 5.2.1 `build_system_prompt("查询订单时展示：状态、地址、送达时间")` → 末尾含该片段
- [ ] 5.2.2 验证段落分隔：response_style 与 "===" 之间有空行

### 5.3 边界
- [ ] 5.3.1 `build_system_prompt("")` → 与无参调用字节级相等
- [ ] 5.3.2 `build_system_prompt(None)` → 不抛异常，行为同空串（需 type ignore 或 isinstance 检查）

---

## 6. 端到端验证

- [ ] 6.1 启动后端，`GET /chat`（无 skill 命中）→ LLM 收到的 system prompt 不含 "=== 技能指引 ==="
- [ ] 6.2 发送触发 query-order-search 消息 → LLM 收到的 system prompt 含 "=== 技能指引 ===\n查询订单时展示..."
- [ ] 6.3 LLM 回复符合 prompt 引导（展示 status/address/estimated_delivery）
