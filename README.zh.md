# ERP MVP Agent

基于 LLM Tool Calling 的精简 ERP 智能体系统。验证"AI是否可以稳定驱动ERP操作闭环"。

[English Version](README.md)

## 项目概述

**核心能力:** 通过自然语言驱动 ERP 操作，支持智能工具路由和基于风险的审批流程。

```
用户（自然语言）
   ↓
大模型（意图识别 + 工具选择）
   ↓
工具层（ERP操作）
   ↓
模拟ERP（数据存储）
```

## 功能特性

| 功能 | 说明 |
|------|------|
| **自然语言操作ERP** | 通过对话查询订单、库存、供应商 |
| **工具调用** | LLM驱动的路由系统，内置8个工具 |
| **风险分级审批** | SAFE/CAUTION/DANGER三级，支持确认流程 |
| **会话管理** | 多会话支持，localStorage持久化 |
| **错误处理** | 四层错误模型（LLM/TOOL/DATA/SYS） |

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React + Vite（无外部UI库） |
| **后端** | FastAPI (Python) |
| **AI** | LLM API（OpenAI兼容） |
| **数据** | Mock ERP（内存字典） |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+

### 后端安装

```bash
cd app
pip install -r requirements.txt

# 配置环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-3.5-turbo"  # 或 MiniMax 模型

# 启动服务
python -m main
```

### 前端安装

```bash
cd frontend
npm install
npm run dev
```

### 同时启动

使用提供的脚本：

```bash
./start.sh
```

## 使用示例

### 查询订单
```
用户: 订单123现在什么状态？
智能体: 订单123当前状态：运输中，预计6月1日送达。
```

### 创建采购订单
```
用户: 为供应商A创建采购订单：iPhone 15 ×10
智能体: 采购订单已创建：PO-1001
```

### 库存判断
```
用户: iPhone 15还有库存吗？能接100台订单吗？
智能体: 当前库存60台，不足100台，建议拆单或补货。
```

### 修改订单（需审批）
```
用户: 把订单123的收货地址改成北京市朝阳区
智能体: [审批卡片] 确认修改订单123的地址字段？
```

## API 参考

### POST /chat

发送消息并接收智能体响应。

**请求:**
```json
{
  "message": "查询订单123",
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "您好，有什么可以帮您的？"}
  ]
}
```

**响应:**
```json
{
  "reply": "订单123正在运输中",
  "tool_calls": [
    {"tool": "query_order", "args": {"order_id": "123"}, "result": {...}}
  ],
  "pending_action": {
    "id": "act_xxx",
    "summary": "修改订单123地址",
    "detail": {...}
  },
  "error": null
}
```

### POST /chat/confirm

确认或拒绝待审批操作。

**请求:**
```json
{
  "action_id": "act_xxx",
  "approved": true,
  "history": [...]
}
```

## 架构设计

```
/app
  main.py        # API入口
  agent.py       # 智能体核心循环
  tools.py       # 工具注册与执行
  llm.py         # LLM调用封装
  mock_erp.py    # 模拟ERP数据
  approval.py    # 审批流程管理器
  config.py      # 风险级别、限额配置
  errors.py      # 统一错误模型
  intent_detector.py # 意图检测引擎

/frontend/src
  App.jsx        # 根组件
  ChatPage.jsx   # 聊天界面与消息渲染
  ApprovalCard.jsx # 风险审批卡片
  SessionManager.js # 会话状态管理
```

## 工具系统

| 工具 | 风险级别 | 说明 |
|------|---------|------|
| query_order | SAFE | 查询单个订单 |
| query_orders | SAFE | 批量查询订单 |
| query_inventory | SAFE | 查询库存 |
| query_supplier | SAFE | 查询供应商 |
| create_order | CAUTION | 创建采购订单（限额5） |
| update_order | DANGER | 修改订单字段（需审批） |
| cancel_order | DANGER | 取消订单（需审批） |
| delete_order | DANGER | 删除订单（需审批，不可撤销） |
| adjust_inventory | DANGER | 调整库存（需审批） |

## 配置说明

| 环境变量 | 默认值 | 说明 |
|--------|--------|------|
| OPENAI_API_KEY | - | LLM API密钥 |
| OPENAI_BASE_URL | https://api.openai.com/v1 | 自定义API端点 |
| LLM_MODEL | gpt-3.5-turbo | 模型选择 |
| APPROVAL_TTL | 300 | 审批超时时间（秒） |
| APPROVAL_MAX_PENDING | 10 | 最大待审批数 |
| HISTORY_WINDOW_N | 6 | 上下文窗口大小 |
| TOOL_LIMIT_CREATE | 5 | 创建订单最大数量 |
| TOOL_LIMIT_UPDATE | 5 | 修改订单最大数量 |
| TOOL_LIMIT_BATCH | 10 | 批量查询最大数量 |
| INTENT_RULES_PATH | app/config/intent_rules.json | 意图规则文件路径 |

## 安全校验

### 双层验证架构

防止LLM幻觉导致高风险操作绕过审批：

| 节点 | 验证内容 | 处理方式 |
|------|---------|---------|
| 节点1 | 工具调用验证 | 检测缺失tool_calls → 意图检测 → 强制二次调用 |
| 节点2 | 审批流程验证 | 确保DANGER工具创建pending_action |

### 意图检测引擎

- **可配置**：JSON文件包含中英文正则模式
- **运行时重载**：调用 `reload_intent_rules()` 应用新规则
- **自定义路径**：设置 `INTENT_RULES_PATH` 环境变量

## 扩展路线

| 阶段 | 内容 |
|------|------|
| Phase 2 | PostgreSQL持久化 + LangGraph状态机 |
| Phase 3 | 真实ERP适配器（SAP/Odoo） |
| Phase 4 | 权限系统（RBAC） |
| Phase 5 | 工作流引擎 + 审批流 |
| Phase 6 | RAG知识库 |

## 许可证

AGPL-3.0
