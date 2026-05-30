# Proposal: Agent Session Logging

## Why

当前 Agent 层缺少调用过程日志记录，出现问题时难以定位排查。通过按会话保存结构化日志文件，支持事后重放分析和精准问题定位，同时帮助理解 AI 模型的调用决策过程。

## What Changes

- 新增 `app/agent_logger.py` 模块，提供 `SessionLogger` 类
- 在 `agent.py` 的关键节点埋入日志调用
- 按日期+session_id 生成独立 JSONL 日志文件
- 实现自动清理逻辑：保留最近 30 个会话、最多 7 天
- 日志类型覆盖：session_start/end、llm_request/response、tool_call/result、approval_pending/result、error

## Capabilities

### New Capabilities

- `agent-session-logging`: 结构化会话日志系统，支持事件通道记录、自动清理、JSONL 格式持久化

## Impact

- 新增文件：`app/agent_logger.py`
- 修改文件：`app/agent.py`（埋入日志调用）
- 依赖：标准库 `json`, `pathlib`, `datetime`，无外部依赖