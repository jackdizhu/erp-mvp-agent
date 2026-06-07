# Design: Agent Session Logging

## Context

当前 `app/agent.py` 的 `chat()` 和 `stream_chat()` 函数缺少调用过程追踪，出现问题只能靠日志盲猜。需求是按会话保存结构化日志到 `logs/` 目录，支持调试定位和调用过程分析。

## Goals / Non-Goals

**Goals:**
- 按 session_id + 日期生成独立 JSONL 日志文件
- 记录完整调用链路：LLM 请求/响应、工具调用/结果、审批流程
- 自动清理：保留最近 30 个会话或 7 天内数据
- 零外部依赖，纯标准库实现

**Non-Goals:**
- 不做日志实时分析/可视化（仅持久化）
- 不做异步写入优化（同步写）
- 不做日志加密/脱敏（仅简单脱敏 api_key）

## Decisions

### 1. SessionLogger 类设计

```
┌─────────────────────────────────────────────────────────────┐
│                     SessionLogger                            │
├─────────────────────────────────────────────────────────────┤
│  __init__(session_id, log_dir="log")                       │
│  ├── _ensure_clean()  → 自动清理过期文件                    │
│  ├── _write(event_type, data)  → 写入 JSONL                │
│  │                                                        │
│  ├── log_session_start(message)                            │
│  ├── log_llm_request(messages)                             │
│  ├── log_llm_response(response)                            │
│  ├── log_tool_call(tool, args, risk_level)                 │
│  ├── log_tool_result(tool, result, error)                  │
│  ├── log_approval_pending(action)                          │
│  ├── log_approval_result(action_id, approved)              │
│  ├── log_error(error_type, message, stack)                 │
│  └── log_session_end(duration_ms)                          │
└─────────────────────────────────────────────────────────────┘
```

**为什么单例不是好选择？**
- 每个会话需要独立的 session_id 和文件路径
- 避免并发写入同一文件
- 每个请求创建新实例，会话结束后自然释放

### 2. 日志格式 (JSONL)

每行一个 JSON 对象，便于 `grep` / `jq` 过滤：

```json
{"timestamp":"2026-05-30T15:30:00","type":"llm_request","session_id":"abc123","data":{"messages":[...]}}
{"timestamp":"2026-05-30T15:30:01","type":"tool_call","session_id":"abc123","data":{"tool":"get_order","args":{"id":123},"risk":"SAFE"}}
```

**为什么不用每条日志单独文件？**
- 减少文件系统 inode 消耗
- 便于批量分析工具读取
- 与 `tail -f` 兼容

### 3. 脱敏策略

LLM 请求中的 `messages` 可能包含用户敏感信息，仅脱敏：
- `api_key` 字段替换为 `"***REDACTED***"`
- 不做全文脱敏，保留可调试性

### 4. 清理策略

```python
def _ensure_clean(self):
    files = sorted(log_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
    if len(files) > 30:
        for f in files[:-30]:  # 保留最新的 30 个
            f.unlink()
    cutoff = datetime.now() - timedelta(days=7)
    for f in files:
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
```

**触发时机**：每个新 SessionLogger 实例创建时执行

**为什么不实现定时任务？**
- 轻量级场景不需要守护进程
- 下次写入时顺便清理，延迟可接受

### 5. 与 agent.py 集成

关键埋入点：

| 函数 | 埋入点 | 日志类型 |
|------|--------|---------|
| `chat()` | 入口 | `session_start` |
| `chat()` | call_llm 前 | `llm_request` |
| `chat()` | call_llm 后 | `llm_response` |
| `chat()` | 工具执行前 | `tool_call` |
| `chat()` | 工具执行后 | `tool_result` |
| `chat()` | 异常 | `error` |
| `chat()` | 结束 | `session_end` |
| `stream_chat()` | 同上 + 流式 chunk | `stream_chunk` |

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| 日志写入失败阻塞请求 | 高 | 捕获写入异常，不影响主流程 |
| 磁盘空间耗尽 | 中 | 30 个文件上限 + 7 天清理 |
| 敏感信息泄露 | 低 | 仅脱敏 api_key |
| 并发写入同一文件 | 低 | 每个会话独立文件 |

## Migration Plan

1. **创建** `app/agent_logger.py`
2. **修改** `app/agent.py`，在关键节点插入 `self._logger.log_xxx()`
3. **创建** `logs/.gitkeep` 确保目录存在
4. **测试**：模拟 35 个会话，验证自动清理

**Rollback**：删除 `app/agent_logger.py`，回滚 `agent.py` 埋点代码

## Open Questions

- [ ] `session_id` 如何生成？（UUID？前端传入？）
- [ ] 流式输出的 chunk 是否需要全部记录？（量大，可能需采样）