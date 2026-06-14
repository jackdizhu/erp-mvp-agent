# Tasks: skill-system-prompt-dynamic

> 对应 spec: [skill-system-prompt-dynamic](../specs/skill-system-prompt-dynamic/spec.md)
> 覆盖原 tasks.md 组 8（prompt_config）/ 组 9（agent Phase 1）/ 组 10（llm.py 清理）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/prompt_config.py` | 修改 | +5 | `build_system_prompt` 新增 `skill_fragments` 参数 |
| `app/llm.py` | 修改 | -1 | 删除模块级 `SYSTEM_PROMPT` 常量（决策 2） |
| `app/agent.py` | 修改 | +10 | `build_messages` 接受 `skill_fragments`，调 `build_system_prompt` |

---

## 1. `app/prompt_config.py` 修改

### 1.1 函数签名变更
- [ ] 1.1.1 将 `def build_system_prompt() -> str:` 改为 `def build_system_prompt(skill_fragments: str = "") -> str:`
- [ ] 1.1.2 关键点：默认参数保证向后兼容（旧调用方无需修改）

### 1.2 注入逻辑
- [ ] 1.2.1 在函数末尾追加：
  ```python
  if skill_fragments:
      parts.append("")
      parts.append("=== 技能指引 ===")
      parts.append(skill_fragments)
  ```
- [ ] 1.2.2 空字符串时不追加 section（避免冗余空行）

### 1.3 __all__ 更新
- [ ] 1.3.1 确认 `__all__ = ["build_system_prompt", "build_capabilities_list"]` 仍正确

### 1.4 单元测试
- [ ] 1.4.1 `build_system_prompt()` 无参调用 → 输出不含 "=== 技能指引 ==="
- [ ] 1.4.2 `build_system_prompt("查询订单...")` → 输出末尾含该片段
- [ ] 1.4.3 `build_system_prompt("")` → 与无参调用字节级相等

---

## 2. `app/agent.py` 修改

### 2.1 import 清理
- [ ] 2.1.1 删除 `from app.llm import call_llm, call_llm_stream, SYSTEM_PROMPT` 中的 `SYSTEM_PROMPT`（决策 2）
- [ ] 2.1.2 改为 `from app.llm import call_llm, call_llm_stream`
- [ ] 2.1.3 添加 `from app.prompt_config import build_system_prompt`

### 2.2 build_messages 改造
- [ ] 2.2.1 将 `def build_messages(message: str, history: list) -> list:` 改为 `def build_messages(message: str, history: list, skill_fragments: str = "") -> list:`
- [ ] 2.2.2 替换 `messages = [{"role": "system", "content": SYSTEM_PROMPT}]` 为：
  ```python
  system_prompt = build_system_prompt(skill_fragments)
  messages = [{"role": "system", "content": system_prompt}]
  ```
- [ ] 2.2.3 关键点：`build_system_prompt` 在 `build_messages` 内调用，确保每次按需拼装

### 2.3 调用方更新
- [ ] 2.3.1 `chat()` 中 `build_messages(message, history)` → `build_messages(message, history, skill_fragments=matched_skill.prompt_fragment if matched_skill else "")`
- [ ] 2.3.2 `stream_chat()` 中同样更新
- [ ] 2.3.3 关键点：未命中 skill 时传空串（与原行为字节级一致）

### 2.4 ENABLE_SKILL 标志
- [ ] 2.4.1 在 `app/config.py` 添加 `ENABLE_SKILL: bool = False`（Phase 1 默认 false）
- [ ] 2.4.2 在 `chat()` / `stream_chat()` 顶部：
  ```python
  matched_skill = None
  if ENABLE_SKILL:
      registry = get_skill_registry()
      if registry:
          matched_skill = registry.match_skill(message)
  ```
- [ ] 2.4.3 关键点：Phase 1 时 `ENABLE_SKILL=False`，`matched_skill` 始终为 None，行为与现状完全一致

---

## 3. `app/llm.py` 清理

### 3.1 删除模块级常量
- [ ] 3.1.1 删除 `SYSTEM_PROMPT = build_system_prompt()`（第 21 行）
- [ ] 3.1.2 **保留** `from app.prompt_config import build_system_prompt`（供其他地方按需调用）

### 3.2 Phase 1 兼容性
- [ ] 3.2.1 验证无其他模块 import `SYSTEM_PROMPT`：`grep -r "from app.llm import.*SYSTEM_PROMPT" .`
- [ ] 3.2.2 关键点：Phase 1 期间**先**改 agent.py，再删 llm.py 常量（避免 ImportError）

### 3.3 单元测试
- [ ] 3.3.1 验证 `app/llm.py` 无 `SYSTEM_PROMPT =` 赋值语句
- [ ] 3.3.2 验证 `from app.llm import SYSTEM_PROMPT` 在项目内**零**次出现
- [ ] 3.3.3 验证 `build_messages("hi", [], skill_fragments="")` 输出与 Phase 0 完全一致（字节级）

---

## 4. Phase 2 启用（决策 1 强语义）

- [ ] 4.1 修改 `app/config.py`：`ENABLE_SKILL: bool = True`
- [ ] 4.2 端到端验证：发送 "查一下订单 ORD-001 状态" → LLM 收到的 system prompt 含 query-order-search 的 prompt_fragment
- [ ] 4.3 端到端验证：发送未匹配消息 → LLM 收到的 system prompt **不**含技能指引
