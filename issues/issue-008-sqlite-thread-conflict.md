---
title: "BUG: SQLite 数据库访问线程冲突导致系统异常"
status: closed
labels: ["bug", "backend", "sqlite", "threading", "erp-service"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

流式聊天接口（`/chat/stream`）在子线程中调用 ERP 工具时，SQLite 数据库访问抛出线程冲突异常，用户收到 "系统异常，请联系系统管理员处理" 错误。

**复现步骤：**
1. 用户发送查询消息触发流式响应
2. LLM 返回工具调用（如 `query_order`）
3. `stream_chat` 在 `threading.Thread` 中执行 `_execute_safe` → `erp_client.execute_tool` → `query_order` → `get_connection()`
4. SQLite 检测到连接由主线程创建但被子线程使用，抛出 `ProgrammingError`

**实际结果：** 流式响应中断，返回 `SYS_ERROR`
**期望结果：** 工具正常执行，流式响应完整返回

## 根因分析

`erp_app/db.py` 使用全局单例 `_conn` 管理 SQLite 连接：

```python
_conn: Optional[sqlite3.Connection] = None

def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)  # 主线程创建
    return _conn  # 子线程复用，跨线程访问报错
```

**触发链路：**
```
app/main.py:stream_endpoint
  → threading.Thread(target=run_sync)    # 子线程
  → stream_chat() → _execute_safe()
  → erp_client.execute_tool()
  → query_order() → get_connection()     # 拿到主线程的连接 → ProgrammingError
```

SQLite 默认 `check_same_thread=True`，禁止跨线程共享连接对象。

## 解决方案

使用 `threading.local()` 实现线程局部存储，每线程独立连接：

```python
_local = threading.local()
_init_lock = threading.Lock()

def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        with _init_lock:
            _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn
```

**修改文件：**
- `erp_app/db.py`

**关键设计：**
- `threading.local()` 每线程独立存储连接实例
- `_init_lock` 防止并发初始化竞争
- WAL 模式支持多连接并发读取

## 验证

- `/chat` 接口正常响应（LLM 调用 + ERP 工具执行）
- `/erp/tools/schemas` 并发查询正常
- `/erp/tools/execute` 支持全部 9 个工具
- 流式响应中工具调用无线程冲突错误
