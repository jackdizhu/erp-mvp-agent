## Why

LLM 流式响应的日志碎片化严重：每个 token 生成一条日志记录（如"订"、"单"、"查"、"询"各一条），一个 340 字符的响应产生 160 条记录，90%+ 是 JSON 开销。这导致：
- 日志文件体积膨胀（160 条 × ~80 字节 ≈ 12.8KB vs 原本 ~400 字节）
- I/O 性能下降（每条记录单独写入）
- 日志可读性差，难以追踪 LLM 输出逻辑

根因：`SessionLogger.log_stream_chunk` 每收到一个 chunk 立即写入，无缓冲。

## What Changes

- 修改 `app/agent_logger.py` 的 `SessionLogger` 类：
  - 新增 `STREAM_BUFFER_SIZE = 30`（累积 30 字符后写入）和 `STREAM_FLUSH_INTERVAL = 0.1`（100ms 超时写入）常量
  - 新增实例变量：`_stream_buffer`、`_stream_last_write`、`_stream_timer`、`_stream_lock`
  - 重写 `log_stream_chunk` 方法：累积内容到缓冲区，达到阈值立即写入，未达到阈值设置定时器超时后写入
  - 新增 `_flush_stream_buffer()` 和 `_delayed_flush()` 辅助方法

## Capabilities

### Modified Capabilities

- `agent-logger`: SessionLogger 的 log_stream_chunk 方法改为缓冲区批量写入模式，减少日志记录数 95%+（160 条 → ~6 条），同时保持日志内容完整性

## Impact

- **修改文件**: `app/agent_logger.py`（1 个文件）
- **日志记录数**: 减少 ~95%（160 条 → ~6 条）
- **向后兼容**: 完全兼容，日志内容不变，仅合并写入时机
- **性能收益**: 减少文件 I/O 次数，提高日志写入效率