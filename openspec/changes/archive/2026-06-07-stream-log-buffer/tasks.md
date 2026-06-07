## 1. SessionLogger 缓冲区实现

- [x] 1.1 在 `app/agent_logger.py` 的 SessionLogger 类中添加类常量 `STREAM_BUFFER_SIZE = 30` 和 `STREAM_FLUSH_INTERVAL = 0.1`
- [x] 1.2 添加实例变量：`_stream_buffer` (str, 默认 ""), `_stream_last_write` (datetime), `_stream_timer` (Timer), `_stream_lock` (Lock)
- [x] 1.3 在 `__init__` 中初始化流式日志相关的实例变量

## 2. log_stream_chunk 重写

- [x] 2.1 重写 `log_stream_chunk` 方法，实现缓冲区逻辑：
  - 获取锁
  - 追加内容到 _stream_buffer
  - 取消待执行的定时器
  - 判断是否达到阈值或超时，决定立即写入或设置定时器
- [x] 2.2 实现 `_flush_stream_buffer()` 方法，将缓冲区内容写入日志文件并清空缓冲区
- [x] 2.3 实现 `_delayed_flush()` 方法，作为定时器回调调用 _flush_stream_buffer

## 3. 线程安全验证

- [x] 3.1 验证多线程同时调用 log_stream_chunk 时不会出现竞争条件
- [x] 3.2 验证缓冲区在并发场景下数据完整性

## 4. 集成验证

- [x] 4.1 模拟发送多个小 chunk（10 个 2 字符），验证合并为 1-2 条记录
- [x] 4.2 验证 STREAM_BUFFER_SIZE=30 阈值触发
- [x] 4.3 验证 STREAM_FLUSH_INTERVAL=100ms 超时触发
- [x] 4.4 验证日志内容完整性（合并后仍是原文）
