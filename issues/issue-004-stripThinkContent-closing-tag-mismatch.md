---
title: "BUG: stripThinkContent 中 <think> 闭标签检测错误"
status: closed
labels: ["bug", "frontend", "streaming"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

修复 `for...of` 遍历问题后，`</think>` 标签仍然未被正确识别，用户仍能看到 `</think>` 后的内容前缀。

**复现步骤：**
1. 发送查询触发 AI 使用 `<think>` 标签
2. 观察输出，发现 `</think>` 后的内容不完整或有残留

## 根因分析

`ChatPage.jsx` 中 `stripThinkContent` 函数：

```js
} else if (chunk.substring(i, i + 8) === "<think>") {
```

第 176 行检测闭标签时错误使用了 `"<think>"` 而非 `"</think>"`。导致：
- 开标签 `<think>`（7字符）命中，`thinkDepth++`
- 闭标签 `</think>`（8字符）被误认为开标签，`thinkDepth` 继续增加而非减少

## 解决方案

将第 176 行的字符串修正：

```js
} else if (chunk.substring(i, i + 8) === "</think>") {
  thinkDepth--;
  i += 8;
}
```

**修改文件：** `frontend/src/ChatPage.jsx`

## 验证

流式响应中 `<think>...</think>` 完整内容被正确过滤。
