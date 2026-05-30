---
title: "BUG: 审批按钮点击 loading 后消失"
status: closed
labels: ["bug", "frontend", "ui", "approval"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: "agent"
---

## 问题描述

审批卡片增加 loading 防重复点击功能后，点击"确认执行"或"取消操作"按钮时，整个按钮区域消失。

**复现步骤：**
1. 触发需要审批的操作（如修改/删除订单）
2. 审批卡片出现，显示"确认执行"和"取消操作"按钮
3. 点击任一按钮

**实际结果：** 按钮区域立即消失
**期望结果：** 按钮变为 disabled 状态并显示 loading 文案

## 根因分析

`ApprovalCard.jsx` 中：

```js
const isPending = status === "pending" && !actionLoading;
```

点击按钮后 `actionLoading` 变为 `true`，导致 `isPending` 变为 `false`，而按钮渲染在 `{isPending && (...)}` 条件内，整个区域被隐藏。

## 解决方案

1. 移除 `isPending` 中的 `!actionLoading` 条件：
   ```js
   const isPending = status === "pending";
   ```

2. 在点击处理函数中增加防重复点击守卫：
   ```js
   const handleConfirm = () => {
     if (actionLoading) return;
     setActionLoading("confirm");
     onConfirm();
   };
   ```

**修改文件：** `frontend/src/ApprovalCard.jsx`

## 验证

点击按钮后，按钮区域保持显示，两个按钮变为 disabled 状态，文案切换为 loading 状态。
