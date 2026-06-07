---
title: "BUG: Agent 日志未写入问题定位与修复"
status: closed
labels: ["bug", "agent", "logging"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

前端调用订单查询、订单信息修改等操作后，`logs/` 目录下没有生成对应的日志文件。

**复现步骤：**
1. 前端发起聊天请求（如"查询订单123"）
2. 执行订单查询或修改操作
3. 检查 `logs/` 目录

**实际结果：** 无日志文件生成

**期望结果：** 每次会话应生成 `{date}_{session_id}.jsonl` 日志文件

## 根因分析

### 问题 1：前端未传递 session_id

前端 `ChatPage.jsx` 和 `useStreamingChat.js` 发起请求时未传递 `session_id` 字段：

```js
// ChatPage.jsx - /chat 请求
body: JSON.stringify({ message: userMsg, history })
// 缺少 session_id

// useStreamingChat.js - /chat/stream 请求
body: JSON.stringify({ message, history })
// 缺少 session_id
```

### 问题 2：后端 logger 创建逻辑错误

`main.py` 中日志创建条件判断有 bug：

```python
# 第 86-88 行
session_id = req.session_id or str(uuid.uuid4())[:8]
logger = SessionLogger(session_id) if req.session_id is not None else None
#                              ↑ 问题在这里！用的是 req.session_id，不是 session_id
```

当 `req.session_id` 为 `None` 时：
- `session_id` 变量已正确生成（备用 UUID）
- 但 `logger` 创建判断用了原始 `req.session_id`
- 导致 `logger = None`，不写入任何日志

### 问题 3：session_id 格式过长

初始修复使用 `uuid.uuid4()` 生成完整 UUID：

```python
session_id = req.session_id if req.session_id else f"none_{uuid.uuid4()}"
# 生成: none_b94f0b28-e2b8-48ae-b24e-1e0731b392ec (36字符)
```

文件名过长，应截断为 8 字符。

## 解决方案

### 1. 前端添加 session_id 传参

**ChatPage.jsx:**
```js
// /chat 请求
body: JSON.stringify({ message: userMsg, history, session_id: activeId })

// /chat/confirm 请求
body: JSON.stringify({ action_id: actionId, approved, history, session_id: activeSession.id })
```

**useStreamingChat.js:**
```js
// 修改函数签名
const startStream = useCallback(async (message, history, session_id, callbacks) => {
  // ...
  body: JSON.stringify({ message, history, session_id })
});
```

**ChatPage.jsx 调用处:**
```js
await startStream(userMsg, truncateHistory(activeSession.messages), activeId, {...})
```

### 2. 后端修复 logger 创建逻辑

```python
# 始终创建 Logger，使用 f-string 格式化
session_id = req.session_id if req.session_id else f"none_{uuid.uuid4().hex[:8]}"
logger = SessionLogger(session_id)
```

### 3. 缩短 session_id 格式

使用 `uuid.uuid4().hex[:8]` 生成 8 字符短 ID：

```python
f"none_{uuid.uuid4().hex[:8]}"
# 生成: none_a1b2c3d4 (12字符)
```

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `frontend/src/ChatPage.jsx` | 添加 session_id 传参到 /chat 和 /chat/confirm |
| `frontend/src/useStreamingChat.js` | 添加 session_id 参数和请求体 |
| `app/main.py` | 修复 logger 创建逻辑，缩短 session_id 格式 |

## 验证

1. 重启后端服务
2. 前端发起聊天请求
3. 检查 `logs/` 目录，应生成 `2026-05-30_{session_id}.jsonl` 文件
4. 无 session_id 时生成 `none_{8位hex}.jsonl` 文件

---

## 追加问题：审批确认日志缺失

**发现问题时间：** 2026-05-30

**现象：** 审批同意/不同意后，日志中只有 `approval_pending`，没有 `approval_result`

**根因：** `ChatPage.jsx` 中有两处 `/chat/confirm` 调用，第二处未传 `session_id`

**修复：** 创建 `httpUtils.js` 统一管理所有 API 调用

---

## 追加修复：统一 API 调用层

### 创建 httpUtils.js

新建 `frontend/src/httpUtils.js`，导出统一的 API 调用函数：

```js
export async function chatPost(sessionId, message, history) {
  return res.json();
}

export async function chatConfirm(sessionId, actionId, approved, history) {
  return res.json();
}

export async function chatStreamReader(sessionId, message, history, callbacks) {
  // SSE 解析逻辑
}
```

### 修改 ChatPage.jsx

```js
import { chatPost, chatConfirm } from './httpUtils';

// 使用统一方法
const data = await chatPost(activeId, userMsg, history);
const data = await chatConfirm(activeSession.id, actionId, approved, history);
```

### 修改 useStreamingChat.js

```js
import { chatStreamReader } from './httpUtils';

await chatStreamReader(session_id, message, history, callbacks);
```

## 最终修改文件清单

| 文件 | 操作 | 修改内容 |
|-----|------|---------|
| `frontend/src/httpUtils.js` | 新增 | 统一 API 调用模块 |
| `frontend/src/ChatPage.jsx` | 修改 | 使用 chatPost/chatConfirm |
| `frontend/src/useStreamingChat.js` | 修改 | 使用 chatStreamReader |
| `app/main.py` | 修改 | 修复 logger 逻辑、session_id 格式 |

## 最终验证

- ✅ 聊天请求生成日志文件
- ✅ 审批确认生成 `approval_result` 日志
- ✅ 流式响应生成完整日志
- ✅ session_id 格式统一（前端传或后端生成 `none_{8位hex}`）