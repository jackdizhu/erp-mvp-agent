---
title: "BUG: 流式完成失败时缺少前端错误提示"
status: closed
labels: ["bug", "frontend", "streaming", "error-handling"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

后端返回错误（如 `LLM_INVALID_RESPONSE: "Connection error."`）时，前端仅关闭 loading 状态，不展示错误信息给用户。

**复现步骤：**
1. 发送查询触发流式响应
2. 后端 LLM 连接失败，返回：
   ```json
   {
     "complete": false,
     "error": {
       "code": "LLM_INVALID_RESPONSE",
       "message": "AI返回异常，请重新提问",
       "recoverable": true
     }
   }
   ```

**实际结果：** 用户看到消息卡片，但无错误提示
**期望结果：** 显示明确的错误信息告知用户处理失败

## 根因分析

`ChatPage.jsx` 中 `onDone` 回调未处理 `data.error` 字段：

```js
msg.content = finalContent;
msg.replyContent = "";
```

直接赋值 `finalContent`（此时为空字符串），错误信息丢失。

## 解决方案

`onDone` 中增加错误分支：

```js
if (data.error) {
  msg.content = data.error.message || "处理失败，请重试";
  msg.errorMessage = data.error.message || "处理失败，请重试";
  msg.errorRecoverable = data.error.recoverable !== false;
} else {
  msg.content = finalContent;
  msg.replyContent = "";
}
```

`StreamingMessage.jsx` 中增加错误横幅渲染：

```js
{message.errorMessage && (
  <div className="error-message-banner">
    <span className="error-icon">⚠️</span>
    <span className="error-text">{message.errorMessage}</span>
  </div>
)}
```

`App.css` 新增 `.error-message-banner` 样式。

**修改文件：**
- `frontend/src/ChatPage.jsx`
- `frontend/src/StreamingMessage.jsx`
- `frontend/src/App.css`

## 验证

后端返回错误时，前端显示红色警告横幅，包含错误图标和错误文本。
