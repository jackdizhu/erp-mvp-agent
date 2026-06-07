---
title: "[Bug] 审批功能不生效 - 点击确认后仍提示请确认"
status: closed
labels: ["bug", "approval-flow"]
created: "2026-06-07"
closed: "2026-06-07"
assignee: ~
---

## 问题描述

审批功能不生效，用户点击"确认执行"后仍提示"请确认"。

**复现步骤：**
1. 用户与 ERP Agent 对话，触发 DANGER 级别工具（如 update_order）
2. Agent 返回 pending_action，前端展示审批卡片
3. 用户点击"确认执行"按钮
4. 系统再次返回 pending_action，而非执行结果
5. 循环往复，无法真正执行操作

**实际结果：**
用户点击确认后，系统仍返回 pending_action，提示用户确认，陷入审批循环

**期望结果：**
用户确认后，工具应直接执行并返回执行结果

## 根因分析

1. **MCP 路由导致二次审批**
   - `confirm_action` 直接调用 `client_factory.execute_tool`
   - 该调用经过 MCP Client 路由到 MCP Service
   - MCP Service 对 DANGER 工具会创建新的审批（新的 `action_id`）
   - 导致工具执行结果返回 `PENDING` 状态而非实际执行结果

2. **LLM 触发重复审批循环**
   - `_generate_reply_from_results` 将 PENDING 结果放入消息上下文后调用 LLM
   - LLM 看到 PENDING 状态后会再次尝试调用工具
   - 触发新的审批循环

3. **意图检测未检查审批状态**
   - `detect_tool_intent` 未检查审批状态
   - 无法区分"已审批待执行"和"新发起待审批"

## 解决方案

### 整体流程重构

```
Agent 检测 DANGER 工具
  ↓
创建审批 → 返回 pending_action 给前端
  ↓
前端收到审批信息 → 调用 POST /api/approval/create
  ↓
后端验证审批（是否支持、字段格式、值格式）→ 返回 { supported: true/false, ... }
  ↓
前端展示审批卡片（supported=false 时无操作按钮）
  ↓
用户点击同意/不同意 → 调用 POST /api/approval/decide
  ↓
后端更新审批记录（添加 user_op_id、审批结果）→ 返回 { user_op_id, approved }
  ↓
前端发送 user_op_id + approved 给 Agent → POST /chat/confirm（携带 user_op_id）
  ↓
Agent detect_tool_intent 检测到已有 user_op_id → 直接执行，不重复审批
  ↓
执行工具 → 返回执行结果
```

### 核心变更

| 序号 | 文件 | 变更类型 | 说明 |
|------|------|---------|------|
| 1 | `app/models.py` | **新建** | 审批 API 请求/响应 Pydantic 模型 |
| 2 | `app/approval_store.py` | **新建** | 审批持久化存储（替换内存 dict） |
| 3 | `app/main.py` | **修改** | 新增 `/api/approval/create`、`/api/approval/decide` 端点 |
| 4 | `app/agent.py` | **修改** | `confirm_action` 重写：路由模式判断 + 传入 `user_op_id` |
| 5 | `app/clients/mcp_client.py` | **修改** | 新增 `execute_tool_preapproved` 方法，`call_tool` 支持 `params` |
| 6 | `app/approval_core.py` | **修改** | `confirm` 方法增加 `user_op_id` 记录 |
| 7 | `app/intent_detector.py` | **修改** | 新增 `check_approval_status` 函数 |
| 8 | `frontend/src/httpUtils.js` | **修改** | 新增 `approvalCreate`、`approvalDecide` 函数 |
| 9 | `frontend/src/ApprovalCard.jsx` | **修改** | 支持审批不支持态（无按钮）、增加两阶段确认 |
| 10 | `frontend/src/ChatPage.jsx` | **修改** | `handleConfirm` 改为两阶段流程 |

### 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 审批存储 | 新建 `approval_store.py`（保留内存 + 为持久化预留接口） | 当前 MVP 阶段保持内存存储，但结构化为独立模块便于后续扩展 Redis/DB |
| 工具执行 | `confirm_action` 使用 `client_factory.execute_tool` + 路由判断 | 按模式路由：MCP 工具用 `execute_tool_preapproved`，ERP 工具直接执行 |
| `detect_tool_intent` | 增加 `check_approval_status` 检查 | 如果已有 user_op_id，直接执行不重复审批 |
| 审批不支持态 | 后端返回 `supported: false`，前端隐藏按钮 | 用户无法对不支持的操作进行审批 |
| user_op_id 格式 | `uop_{uuid.hex[:12]}` | 与 `act_` 前缀区分，便于日志追踪 |

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `app/models.py` | 新建：ApprovalCreateRequest、ApprovalCreateResponse、ApprovalDecideRequest、ApprovalDecideResponse |
| `app/approval_store.py` | 新建：ApprovalRecord 类、ApprovalStore 类、approval_store 单例 |
| `app/main.py` | 修改：新增 POST /api/approval/create、POST /api/approval/decide 端点 |
| `app/agent.py` | 修改：confirm_action 重写，路由模式判断 + 传入 user_op_id |
| `app/clients/mcp_client.py` | 修改：新增 execute_tool_preapproved 方法，call_tool 支持 params 参数 |
| `app/approval_core.py` | 修改：confirm 方法增加 user_op_id 记录 |
| `app/intent_detector.py` | 修改：新增 check_approval_status 函数 |
| `frontend/src/httpUtils.js` | 修改：新增 approvalCreate、approvalDecide、chatConfirmWithUserOp 函数 |
| `frontend/src/ApprovalCard.jsx` | 修改：支持 supported=false 状态隐藏按钮 |
| `frontend/src/ChatPage.jsx` | 修改：handleConfirm 改为两阶段流程 |

## 验证

- [x] 正常审批流程：用户点击确认 → 两阶段执行 → 不再重复审批
- [x] 审批不支持态：不支持的操作显示灰色卡片，无按钮
- [x] 重复点击防护：actionLoading 阻止重复请求
- [x] 过期审批：后端返回 TOOL_EXPIRED
- [x] 向后兼容：不传 user_op_id 时走原有审批流程

## 敏感信息检查

**脱敏规则：**
| 类型 | 脱敏方式 |
|------|---------|
| 绝对路径 | 使用项目相对路径或 `<path>` 替代 |
| 环境变量 | 使用 `<ENV_VAR>` 替代 |
| 密钥/Token | 使用 `<KEY>` 或 `***` 替代 |
| 用户名/邮箱 | 使用 `<user>`, `<email>` 替代 |
| 会话ID | 使用 `<session>` 替代 |

**检查结果：** 无敏感信息泄露