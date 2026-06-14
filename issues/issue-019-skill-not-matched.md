---
title: "Skill 未正确调用 - ENABLE_SKILL 默认关闭 + 工具格式不匹配 + stream_chat 缺少 skill 逻辑"
status: closed
labels: ["bug", "skill", "observability"]
created: "2026-06-14"
closed: "2026-06-14"
assignee: ~
---

## 问题描述

前端请求 `/chat/stream` endpoint 时，日志中没有 skill 调用事件（`skill_matched`、`skill_fragment_applied`），导致 skill 框架未生效。

**复现步骤：**
1. 启动后端服务器
2. 通过前端发送消息"查询订单123"
3. 检查日志文件 `logs/<date>_<session>.jsonl`
4. 发现日志缺少 `skill_matched` / `skill_fragment_applied` 事件

**实际结果：**
- 日志仅包含 `session_start` → `llm_request` → `tool_call` → `session_end`
- system prompt 不包含 skill fragment
- skill 匹配逻辑未执行

**期望结果：**
- 日志包含 `skill_matched` / `skill_fragment_applied` / `llm_request`（含 skill fragment）
- skill 匹配成功并注入 prompt fragment

## 根因分析

### Bug 1: ENABLE_SKILL 默认关闭

**原因：** `app/config.py` 第 40 行：
```python
ENABLE_SKILL = os.getenv("ENABLE_SKILL", "false").lower() in ("true", "1", "yes")
```

默认值为 `"false"`，导致 `agent.py` 第 48 行直接返回空字符串，跳过 skill 匹配：
```python
if not ENABLE_SKILL:
    return ""
```

**影响：** 所有 skill 匹配逻辑被禁用。

### Bug 2: 工具格式不匹配

**原因：** `agent.py` 第 160 行假设 OpenAI 工具格式：
```python
available_tools=[t["function"]["name"] for t in client_factory.get_all_tools()]
```

但 MCP 工具格式是 `{name: "tool_name", ...}`，不是 `{function: {name: ...}}`。

**错误：** `KeyError: 'function'`，导致 skill 执行失败。

### Bug 3: stream_chat 缺少 skill 匹配逻辑

**原因：** `agent.py` 第 518 行 `stream_chat()` 函数直接调用 `call_llm()`，没有复制 `chat()` 函数的 skill 匹配逻辑（第 129-250 行）。

**影响：** `/chat/stream` endpoint（前端使用）无 skill 功能，仅 `/chat` endpoint（同步）有 skill 功能。

## 解决方案

### Fix 1: 启用 ENABLE_SKILL

在 `.default.env` 第 6 行添加：
```env
ENABLE_SKILL=true
```

### Fix 2: 适配 MCP 工具格式

修改 `agent.py` 第 155-162 行：
```python
all_tools = client_factory.get_all_tools()
available_tools = []
for t in all_tools:
    if "name" in t:
        available_tools.append(t["name"])
    elif "function" in t and "name" in t["function"]:
        available_tools.append(t["function"]["name"])
```

### Fix 3: stream_chat 添加 skill 匹配逻辑

在 `stream_chat()` 函数开头（第 524 行）添加 skill 匹配逻辑：
- 复制 `chat()` 的 skill 匹配逻辑（第 129-250 行）
- 使用 `on_event` 直接传递（不依赖 contextvars）
- 处理 need_approval / failure / success 分支
- 修改 `build_messages()` 添加 `skill_fragments` 参数

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `.default.env` | +`ENABLE_SKILL=true` |
| `app/agent.py` | +工具格式适配（第 155-162 行） |
| `app/agent.py` | +`stream_chat()` skill 匹配逻辑（第 524-612 行） |

## 验证

- ✅ `/chat` endpoint skill 匹配成功（日志含 `skill_matched`）
- ✅ `/chat/stream` endpoint skill 匹配成功（日志含 `skill_matched`）
- ✅ SSE 事件 `skill_matched` 正常发送
- ✅ 日志事件 `skill_matched` / `skill_fragment_applied` 正常记录
- ✅ system prompt 包含 skill fragment

**验证日志示例：**
```json
{"type": "skill_matched", "data": {"skill_name": "query-order-search", "correlation_id": "skill_exec_..."}}
{"type": "skill_fragment_applied", "data": {"fragment_preview": "查询订单时，请展示以下信息..."}}
{"type": "llm_request", "data": {"messages": [{"role": "system", "content": "...=== 技能指引 ===\n查询订单时..."}]}}
```

## 敏感信息检查

已执行检查：
```bash
grep -rE "^[A-Z]:\\\\|:/|api[_-]?key|password|token|secret" issues/issue-019-skill-not-matched.md
# 无敏感信息
```

**脱敏处理：**
- 会话ID: 使用 `<session>` 替代（实际日志中保留用于调试）
- correlation_id: 使用 `skill_exec_...` 替代（实际日志中保留用于追踪）