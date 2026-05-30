---
title: "BUG: replace 正则 /s 标志导致 Vite oxc 解析失败"
status: closed
labels: ["bug", "frontend", "build", "streaming"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

流式完成时清理 `<think>` 标签的正则表达式导致 Vite 构建失败，终端报 4 个 PARSE_ERROR。

**复现步骤：**
1. 在 `ChatPage.jsx` 中使用 `.replace(/<think>.*?<think>/gs, "")` 
2. 保存文件，Vite 编译

**错误信息：**
```
[PARSE_ERROR] Unexpected flag t/h/i/n/k in regular expression literal
Help: The allowed flags are `gimsuydv`
```

## 根因分析

正则表达式 `/<think>.*?<think>/gs` 存在两个问题：

1. **`s` 标志不兼容**：`/s` 是 ES2018 的 dotAll 标志，但 Vite 使用的 oxc 解析器不支持
2. **`/` 转义问题**：`</think>` 中的 `/` 被解析器误认为正则表达式结束符，导致 `t`, `h`, `i`, `n`, `k` 被误解析为标志

## 解决方案

使用 `[\s\S]` 替代 `.` 配合 `s` 标志，并正确转义 `/`：

```js
.replace(/<think>[\s\S]*?<think>/g, "")
```

**修改文件：** `frontend/src/ChatPage.jsx`

## 验证

Vite 编译通过，无正则表达式解析错误。
