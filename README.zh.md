# ERP MVP Agent

基于 LLM Tool Calling 的 ERP 智能体系统。验证"AI是否可以稳定驱动ERP操作闭环"。

[English Version](README.md)

## 项目概述

**核心能力:** 通过自然语言驱动 ERP 操作，支持 MCP 协议多客户端路由、两阶段风险审批和流式响应。

```
用户（自然语言）
   ↓
Skill 匹配（app.skills.registry）— 可选，ENABLE_SKILL=true 时启用
   ↓
Agent（意图识别 + 工具选择 + 强制重试）
   ↓
ClientFactory（MCP / 本地适配器 / 混合路由）
   ↓
ERP 服务（SQLite 持久化 + Service 层）
```

## Skill 框架

系统支持 Skill 机制（[设计文档](docs/design-skill-plan-c.md)）：
- **preset skill**（`skills/{name}/`）：含 `skill.yaml` + 可选 `handler.py`
- **custom skill**（`skills_custom/{name}/`）：仅 `skill.yaml`，YAML 工作流，无代码

管理 API：
- `GET /api/skills/available` — 列出所有 skill
- `POST /api/skills/validate` — 校验配置
- `POST /api/skills/create` — 创建 custom skill（自动写盘 + 热加载）

## 核心优势

| 优势 | 说明 |
|------|------|
| **MCP 协议原生支持** | 实现 MCP Streamable HTTP 规范（2025-11-25），支持 JSON-RPC 2.0、会话管理、异步 Task |
| **多后端智能路由** | ClientFactory 统一调度 MCP 远程服务、本地 ERP 适配器，支持 mcp/hybrid/local 三种模式热切换 |
| **两阶段审批闭环** | 前端验证(ApprovalStore) → 用户决定(user_op_id) → Agent 执行，防止审批绕过 |
| **意图兜底机制** | LLM 未调用工具时，意图检测引擎自动识别并强制二次调用，消除幻觉风险 |
| **全链路可观测** | SessionLogger 记录每轮 LLM 请求/响应/工具调用/审批结果，JSONL 持久化 + 自动清理 |
| **Prompt 外部化** | 系统提示词从代码解耦到 prompts.yaml，支持运行时修改无需重启 |

## 功能特性

| 功能 | 说明 |
|------|------|
| **自然语言操作ERP** | 通过对话查询订单、库存、供应商 |
| **MCP 协议集成** | 完整 MCP Streamable HTTP 实现，支持 SSE/JSON 双模式响应 |
| **工具调用** | LLM 驱动的路由系统，9 个内置工具 + MCP 动态扩展 |
| **风险分级审批** | SAFE/CAUTION/DANGER 三级，两阶段确认流程 |
| **会话管理** | 多会话支持，localStorage 持久化 |
| **流式响应** | SSE 实时推送，打字机效果，工具状态可视化 |
| **错误处理** | 四层错误模型（LLM/TOOL/DATA/SYS）+ MCP 专属错误类型 |
| **会话日志** | JSONL 持久化，流式缓冲写入，7天自动清理 |

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React + Vite（无外部UI库） |
| **Agent 服务** | FastAPI (Python)，端口 9000 |
| **MCP 服务** | FastAPI (Python)，端口 9001，JSON-RPC 2.0 |
| **AI** | LLM API（OpenAI 兼容） |
| **数据** | SQLite（WAL 模式）+ Service 层 |
| **协议** | MCP Streamable HTTP（2025-11-25） |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+

### 配置

复制默认环境变量文件并修改：

```bash
cp .default.env .local.env
# 编辑 .local.env，填入 API Key 等配置
```

### 后端安装

```bash
pip install -r app/requirements.txt

# 启动 Agent 服务（含 ERP 内部服务）
python -m app.main

# 启动 MCP 服务（可选，CLIENT_BACKEND=mcp 时需要）
pip install -r erp_mcp_service/requirements.txt
python -m erp_mcp_service.main
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
  ],
  "session_id": "optional-session-id"
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
    "status": "PENDING",
    "action_id": "act_xxx",
    "tool": "update_order",
    "risk_level": "DANGER",
    "title": "修改订单",
    "summary": "修改订单123的address",
    "description": "...",
    "warning": null,
    "detail": {...},
    "expires_at": 1717200000,
    "ttl_seconds": 300
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
  "history": [...],
  "session_id": "optional-session-id",
  "user_op_id": "uop_xxx"
}
```

### POST /chat/stream

SSE 流式响应，实时推送 Agent 执行状态。

**请求:** 与 `/chat` 相同格式。

**响应:** `text/event-stream` 格式，包含以下事件类型：

| 事件 | 说明 | 数据格式 |
|------|------|---------|
| `thinking` | Agent 思考阶段 | `{"stage": "analyzing_intent", "message": "正在理解您的意图..."}` |
| `tool_call` | 工具调用开始 | `{"tool": "query_order", "args": {...}, "status": "executing"}` |
| `tool_result` | 工具执行结果 | `{"tool": "query_order", "result": {...}, "status": "completed"}` |
| `reply_chunk` | LLM 回复片段 | `{"content": "订"}` |
| `done` | 完成标记 | `{"complete": true, "tool_calls": [...], "pending_action": null}` |

### POST /api/approval/create

前端收到审批信息后，创建审批记录并验证。

**请求:**
```json
{"action_id": "act_xxx"}
```

**响应:**
```json
{
  "supported": true,
  "action_id": "act_xxx",
  "fields": ["address"],
  "irreversible": false,
  "warning": null
}
```

### POST /api/approval/decide

用户点击同意/不同意，生成用户审批操作 ID。

**请求:**
```json
{"action_id": "act_xxx", "approved": true}
```

**响应:**
```json
{
  "user_op_id": "uop_xxx",
  "action_id": "act_xxx",
  "approved": true,
  "status": "approved"
}
```

### POST /api/mcp/reload

热重载 MCP 服务注册表。

### GET /api/mcp/debug

查看 MCP 客户端注册状态。

### GET /health

健康检查，返回服务状态和配置信息。

## 架构设计

```
/app                          # Agent 服务（端口 9000）
  main.py                     # API 入口（7个端点）
  agent.py                    # 智能体核心循环（chat/stream_chat/confirm）
  llm.py                      # LLM 调用封装（同步+流式）
  clients/
    client_factory.py         # 工具路由工厂（MCP/本地适配器/混合）
    mcp_client.py             # MCP 客户端（Streamable HTTP）
    mcp_registry.py           # MCP 服务注册表（热重载）
    erp_adapter.py            # 本地 ERP 适配器
    base.py                   # 客户端基类
  approval_core.py            # 审批核心逻辑（创建/确认/过期清理）
  approval_store.py           # 审批记录存储（两阶段验证）
  intent_detector.py          # 意图检测引擎
  agent_logger.py             # 会话日志（JSONL持久化+流式缓冲）
  prompt_config.py            # Prompt 外部化管理
  config.py                   # 配置中心
  errors.py                   # 统一错误模型
  models.py                   # Pydantic 数据模型
  erp_client.py               # ERP 客户端封装
  config_dir/
    prompts.yaml              # 系统提示词配置
    intent_rules.json         # 意图检测规则
    mcp_servers.json          # MCP 服务注册配置

/erp_app                      # ERP 业务服务（内部模块）
  main.py                     # ERP 内部 API（/erp/tools/*, /erp/approval/*）
  tools.py                    # 工具注册与执行（9个工具）
  tools_format.py             # 工具 Schema 格式化
  db.py                       # SQLite 数据层（WAL模式，线程安全）
  seed.py                     # 种子数据
  models.py                   # 数据模型
  schemas.py                  # Pydantic Schema
  approval_detail.py          # 审批详情生成
  config.py                   # 业务配置
  errors.py                   # 业务错误
  services/
    order_service.py          # 订单服务（创建/修改/取消/删除）
    inventory_service.py      # 库存服务（调整）
    supplier_service.py       # 供应商服务

/erp_mcp_service              # MCP 独立服务（端口 9001）
  main.py                     # MCP Streamable HTTP 端点
  tools.py                    # MCP 工具列表与执行
  approval_manager.py         # MCP 审批管理
  session_manager.py          # MCP 会话管理
  task_manager.py             # 异步任务管理
  config.py                   # MCP 服务配置

/frontend/src
  App.jsx                     # 根组件
  ChatPage.jsx                # 聊天界面与消息渲染
  StreamingMessage.jsx        # 流式消息渲染组件
  ThinkingIndicator.jsx       # 思考状态指示器
  ToolStatusCard.jsx          # 工具状态卡片
  DataVizCard.jsx             # 数据可视化卡片
  ApprovalCard.jsx            # 风险审批卡片
  McpErrorNotification.jsx    # MCP 错误通知组件
  useStreamingChat.js         # SSE 流式连接管理器
  SessionManager.js           # 会话状态管理
  httpUtils.js                # HTTP 工具函数
```

## 工具系统

| 工具 | 风险级别 | 说明 |
|------|---------|------|
| query_order | SAFE | 查询单个订单 |
| query_orders | SAFE | 批量查询订单 |
| query_inventory | SAFE | 查询库存 |
| query_supplier | SAFE | 查询供应商 |
| create_order | CAUTION | 创建订单（限额5项） |
| update_order | DANGER | 修改订单字段（需审批） |
| cancel_order | DANGER | 取消订单（需审批） |
| delete_order | DANGER | 删除订单（需审批，不可撤销） |
| adjust_inventory | DANGER | 调整库存（需审批） |

## 配置说明

| 环境变量 | 默认值 | 说明 |
|--------|--------|------|
| OPENAI_API_KEY | - | LLM API 密钥 |
| OPENAI_BASE_URL | https://api.openai.com/v1 | 自定义 API 端点 |
| LLM_MODEL | gpt-4o | 模型选择 |
| CLIENT_BACKEND | mcp | 工具路由模式：mcp / hybrid / local |
| ENABLE_LOCAL_ADAPTER | false | 启用本地 ERP 适配器 |
| MCP_SERVICE_URL | http://localhost:9001 | MCP 服务地址 |
| MCP_SERVICE_PORT | 9001 | MCP 服务端口 |
| MCP_API_KEY | - | MCP 服务 API 密钥 |
| MCP_RESPONSE_MODE | sse | MCP 响应模式：sse / json / auto |
| BACKEND_PORT | 9000 | Agent 服务端口 |
| APPROVAL_TTL | 300 | 审批超时时间（秒） |
| APPROVAL_MAX_PENDING | 10 | 最大待审批数 |
| HISTORY_WINDOW_N | 6 | 上下文窗口大小 |
| TOOL_LIMIT_CREATE | 5 | 创建订单最大项数 |
| TOOL_LIMIT_UPDATE | 5 | 修改订单最大项数 |
| TOOL_LIMIT_BATCH | 10 | 批量查询最大数量 |
| LLM_TIMEOUT | 15 | LLM 调用超时（秒） |
| MCP_REQUEST_TIMEOUT | 10 | MCP 请求超时（秒） |
| MCP_CONNECT_TIMEOUT | 5 | MCP 连接超时（秒） |
| SSE_PING_INTERVAL | 15 | SSE 心跳间隔（秒） |
| SSE_TIMEOUT | 60 | SSE 连接超时（秒） |
| SSE_MAX_CHUNK | 500 | SSE 最大分片大小 |
| INTENT_RULES_PATH | app/config/intent_rules.json | 意图规则文件路径 |

## 安全校验

### 三层验证架构

防止 LLM 幻觉导致高风险操作绕过审批：

| 节点 | 验证内容 | 处理方式 |
|------|---------|---------|
| 节点1 | 工具调用验证 | 检测缺失 tool_calls → 意图检测 → 强制二次调用 |
| 节点2 | 审批流程验证 | 确保 DANGER 工具创建 pending_action |
| 节点3 | 两阶段审批验证 | ApprovalStore 验证 → 用户决定(user_op_id) → Agent 执行 |

### 意图检测引擎

- **可配置**：JSON 文件包含中英文正则模式
- **运行时重载**：调用 `reload_intent_rules()` 应用新规则
- **自定义路径**：设置 `INTENT_RULES_PATH` 环境变量

### MCP 安全

- **API Key 验证**：MCP 服务支持 X-API-Key 请求头
- **协议版本校验**：初始化时验证客户端协议版本
- **会话隔离**：每个 MCP 客户端独立会话，请求追踪

## 扩展路线

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | MVP 核心闭环 | ✅ 已完成 |
| Phase 2 | SQLite 持久化 + MCP 协议 | ✅ 已完成 |
| Phase 3 | 真实 ERP 适配器（SAP/Odoo） | 规划中 |
| Phase 4 | 权限系统（RBAC） | 规划中 |
| Phase 5 | 工作流引擎 + 审批流 | 规划中 |
| Phase 6 | RAG 知识库 | 规划中 |

## 许可证

AGPL-3.0
