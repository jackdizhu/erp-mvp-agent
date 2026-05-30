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

## ⚠️ 敏感信息脱敏规则

**禁止在文档中暴露以下信息：**

| 类型 | 示例 | 脱敏方式 |
|------|------|---------|
| 绝对路径 | `C:\Users\...` | 使用 `<project>`, `<app>` 等占位符 |
| 环境变量 | `.env`, `OPENAI_API_KEY` | 使用 `*_KEY`, `<ENV_VAR>` 等占位符 |
| 密钥/Token | `sk-xxx`, `api_key=xxx` | 使用 `<KEY>`, `***` 等遮蔽 |
| 用户名/邮箱 | `user@domain.com` | 使用 `<user>`, `<email>` 等占位符 |
| 会话ID | `sess_xxx`, `session_id` | 使用 `<session>` 等占位符 |

**检查命令：**
```bash
# 检查是否包含敏感路径
grep -r "C:\\\|D:\\|/c/" .
# 检查是否包含敏感变量
grep -r "\.env\|api_key\|OPENAI_\|password\|token" .
```