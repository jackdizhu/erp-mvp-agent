## Context

`SessionLogger.log_stream_chunk` 在每次收到 LLM 流式 chunk 时直接调用 `_write()` 写入日志文件。由于 OpenAI API 按 token 粒度返回 chunks（中文每字 1 token），导致日志碎片化：一个 340 字符响应产生 160 条记录，每条 ~80 字节 JSON 开销。

## Goals / Non-Goals

**Goals:**
- 减少日志记录数 95%+（160 条 → ~6 条）
- 保持日志内容完整性（合并后仍包含所有内容）
- 保持向后兼容（不影响其他日志类型）

**Non-Goals:**
- 不修改 LLM 调用逻辑（llm.py）
- 不实现日志轮转或压缩
- 不添加日志分析功能

## Decisions

### Decision 1: 缓冲区 + 定时器混合策略

**选择**: 在 SessionLogger 内部实现缓冲区，累积到阈值（30 字符）或超时（100ms）后写入

**备选方案**:
- A) 固定阈值写入 → 简单但可能延迟太长
- B) 固定时间间隔写入 → 延迟稳定但可能产生小碎片
- C) 缓冲区 + 定时器混合 → 平衡实时性和批量效率 ✓

**理由**: 30 字符阈值捕获大多数中文词组，100ms 超时确保延迟不超过 100ms。

### Decision 2: 线程安全的定时器

**选择**: 使用 `threading.Timer` 实现延迟写入，配合 `threading.Lock` 保证线程安全

**备选方案**:
- A) 简单 time.sleep 延迟 → 阻塞调用线程
- B) asyncio 定时器 → 引入异步复杂度
- C) threading.Timer → 非阻塞，轻量 ✓

**理由**: 日志写入不应阻塞 LLM 流式处理，Timer 是最轻量的非阻塞方案。

### Decision 3: 取消待执行定时器的策略

**选择**: 每次收到新 chunk 时取消旧定时器，重新计时

**理由**: 保证最后一块数据在 100ms 内写入，同时合并中间的小 chunk。

## Risks / Trade-offs

- **[并发写入竞争]** → 多线程同时调用 log_stream_chunk 时可能竞争 `_stream_lock`。**缓解**: 使用 threading.Lock 保证原子性。
- **[定时器未触发]** → 如果进程异常退出，缓冲区数据可能丢失。**缓解**: daemon=True 确保随进程退出；MVP 阶段可接受。
- **[前端延迟感知]** → 缓冲区可能导致前端显示略有延迟（最多 100ms）。**缓解**: 阈值 30 字符足够覆盖大多数中文词组。