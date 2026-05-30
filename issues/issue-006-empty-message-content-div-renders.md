---
title: "BUG: 空 message-content div 节点渲染导致布局异常"
status: closed
labels: ["bug", "frontend", "ui", "streaming"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

流式消息工具调用标签前存在一个空的 `message-content` 节点，导致布局出现额外间距。

**复现步骤：**
1. 发送查询触发工具调用
2. 检查渲染的 DOM 结构

**实际结果：** `tool-call-sequence` 前存在一个空的 `<div class="message-content"></div>`
**期望结果：** 无内容时不应渲染空节点

## 根因分析

`StreamingMessage.jsx` 中：

```js
<div className="message-content">{message.content || ""}</div>
```

当 `message.content` 为空字符串时，`message.content || ""` 仍渲染了一个内容空的 div 元素，占据布局空间。

## 解决方案

改为条件渲染：

```js
{message.content && (
  <div className="message-content">{message.content}</div>
)}
```

**修改文件：** `frontend/src/StreamingMessage.jsx`

## 验证

无内容时 `message-content` div 不再渲染。
