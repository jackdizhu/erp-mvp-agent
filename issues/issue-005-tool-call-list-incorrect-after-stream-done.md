---
title: "BUG: 流式完成后工具调用列表数量减少"
status: closed
labels: ["bug", "frontend", "streaming", "tool-call", "react"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

流式处理过程中正确显示 2 个工具调用，但完成后只显示 1 个。

**复现步骤：**
1. 发送需要多次工具调用的查询
2. 处理过程中观察 `tool-call-sequence`，显示 2 个工具
3. 完成后观察同一消息的 `tool-call-sequence`

**实际结果：** 完成后工具列表减少到 1 个
**期望结果：** 完成后保持完整的工具调用历史

## 根因分析

`ChatPage.jsx` 中 `onToolCall`、`onReplyChunk`、`onDone`、`onError` 的 `updateSessions` 回调使用了**引用变异（mutation）模式**：

```js
updateSessions(prev => {
  const session = prev.find(s => s.id === activeId);
  const msg = session.messages[session.messages.length - 1];
  msg.toolEvents = [...msg.toolEvents, { tool: data.tool }]; // mutation
  return [...prev]; // new array, same session/msg refs
});
```

虽然 `[...prev]` 创建了新的数组引用，但 `session` 和 `msg` 对象引用未改变。React 的 `setState` 在比较状态时可能检测到 `prev` 数组引用变化，但在 `onDone` 时设置 `completedTools = toolCallOrder`，由于之前的 mutation 已经污染了 React 状态树，React 在某些情况下可能跳过重新渲染或使用缓存的旧值。

此外，`onDone` 中 `data.tool_calls`（后端返回）可能只包含最后一次工具调用，当它覆盖前端收集的 `toolCallOrder` 时，列表就会丢失。

## 解决方案

所有 `updateSessions` 回调改为**不可变更新模式**（immutable update），为每一层创建新对象引用：

```js
updateSessions(prev => {
  const idx = prev.findIndex(s => s.id === activeId);
  if (idx === -1) return prev;
  const session = { ...prev[idx] };
  const msgs = [...session.messages];
  const msg = { ...msgs[msgs.length - 1] };
  msg.toolEvents = [...msg.toolEvents, { tool: data.tool }];
  msgs[msgs.length - 1] = msg;
  session.messages = msgs;
  prev[idx] = session;
  return [...prev];
});
```

同时对 `onDone` 中 `completedTools` 和 `toolEvents` 统一使用 `toolCallOrder`：
```js
msg.completedTools = toolCallOrder;
msg.toolEvents = toolCallOrder.map(t => ({ tool: t }));
```

**修改文件：** `frontend/src/ChatPage.jsx`（4 处回调全部修改）

## 验证

流式完成后工具调用列表数量与处理过程中一致，React 正确重新渲染。
