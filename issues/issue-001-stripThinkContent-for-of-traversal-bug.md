---
title: "BUG: stripThinkContent for...of 遍历中修改 chunk 变量无效"
status: closed
labels: ["bug", "frontend", "streaming"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

前端流式响应中 `<think>` 标签内容未被正确过滤，用户仍能看到 AI 思考过程。

**复现步骤：**
1. 发送需要调用工具的查询（如"查询订单123"）
2. 观察流式响应输出

**实际结果：** 输出包含 `<think>订单查询成功，信息已返回...</think>` 原始内容

**期望结果：** `<think>` 标签内容应被完全过滤

## 根因分析

`ChatPage.jsx` 中 `stripThinkContent` 函数使用 `for...of` 逐字符遍历：

```js
for (const char of chunk) {
  if (char === "<") {
    const remaining = chunk.substring(chunk.indexOf(char));
    if (remaining.startsWith("<think>")) {
      thinkDepth++;
      chunk = remaining.substring("<think>".length - 1);
      continue;
    }
  }
  // ...
}
```

问题：
1. `for...of` 迭代器基于原始字符串创建，修改 `chunk` 变量不影响遍历位置
2. `indexOf` 每次都从位置 0 搜索，导致定位错误
3. 开闭标签检测逻辑混乱

## 解决方案

重写为基于索引的 `while` 循环：

```js
const stripThinkContent = (chunk) => {
  let result = "";
  let i = 0;
  while (i < chunk.length) {
    if (chunk.substring(i, i + 7) === "<think>") {
      thinkDepth++;
      i += 7;
    } else if (chunk.substring(i, i + 8) === "</think>") {
      thinkDepth--;
      i += 8;
    } else {
      if (thinkDepth === 0) {
        result += chunk[i];
      }
      i++;
    }
  }
  return result;
};
```

**修改文件：** `frontend/src/ChatPage.jsx`

## 验证

重新测试流式响应，确认 `<think>` 标签内容已完全过滤。
