---
title: "[标题] 问题或功能简述"
status: open
labels: ["bug", "enhancement", "question"]
created: "2026-05-30"
closed: ~
assignee: ~
---

## 问题描述

简要描述问题或需求。

**复现步骤：**
1.
2.
3.

**实际结果：**

**期望结果：**

## 根因分析

（仅 Bug 需要填写）

## 解决方案

（可选）

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
|      |         |

## 验证

-

## 敏感信息检查

创建 issue 后，请执行以下命令检查是否包含敏感信息：

```bash
# 检查敏感路径
grep -rE "^[A-Z]:\\\\|:/" issues/

# 检查敏感变量
grep -rE "api[_-]?key|password|token|secret" issues/
```

**脱敏规则：**
| 类型 | 脱敏方式 |
|------|---------|
| 绝对路径 | 使用项目相对路径或 `<path>` 替代 |
| 环境变量 | 使用 `<ENV_VAR>` 替代 |
| 密钥/Token | 使用 `<KEY>` 或 `***` 替代 |
| 用户名/邮箱 | 使用 `<user>`, `<email>` 替代 |
| 会话ID | 使用 `<session>` 替代 |