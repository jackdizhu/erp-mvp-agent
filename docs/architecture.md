# ERP Agent MVP 项目架构文档

> 基于 LLM Tool Calling 的 ERP 操作型 Agent 系统
> 生成日期: 2026-06-07

---

## 一、系统总览

### 1.1 项目定位

通过自然语言驱动 ERP 操作，支持查询、写入、批处理，以及基于风险分级的审批确认流程。

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────┐
│              React Frontend (Vite)                   │
│  ChatPage · ApprovalCard · StreamingMessage         │
│  SessionManager · useStreamingChat · httpUtils       │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (app/)                  │
│  main.py · agent.py · approval_core.py              │
│  intent_detector · llm · prompt_config              │
│  agent_logger · errors · config                     │
├──────────────────────┬──────────────────────────────┤
│         ClientFactory (工具路由层)                    │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │ ERP Adapter │  │ MCP Registry │                  │
│  │  (本地直连)  │  │  (远程服务)   │                  │
│  └──────┬──────┘  └──────┬───────┘                  │
└─────────┼────────────────┼──────────────────────────┘
          │                │ JSON-RPC / HTTP
          ▼                ▼
┌──────────────┐  ┌───────────────────────────────────┐
│  erp_app/    │  │  erp_mcp_service/                 │
│  (本地ERP)   │  │  (MCP协议服务)                     │
│  SQLite DB   │  │  session · task · approval         │
└──────────────┘  └───────────────────────────────────┘
```

### 1.3 双后端模式

系统支持三种客户端后端模式（通过 `CLIENT_BACKEND` 环境变量配置）：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `local` | 仅使用 ERP Adapter 本地直连 | 单机部署、开发调试 |
| `mcp` | 仅使用 MCP 远程服务 | 微服务部署 |
| `hybrid`（默认） | MCP 优先，本地适配器兜底 | 生产环境推荐 |

---

## 二、目录结构

```
erp-mvp-agent/
├── app/                          # Agent 后端（FastAPI）
│   ├── clients/                  # 客户端抽象层
│   │   ├── base.py               # 客户端基类接口
│   │   ├── client_factory.py     # 工具路由工厂（核心调度）
│   │   ├── erp_adapter.py        # 本地 ERP 适配器
│   │   ├── mcp_client.py         # MCP 协议客户端
│   │   └── mcp_registry.py       # MCP 服务注册中心
│   ├── config_dir/               # 配置文件目录
│   │   ├── intent_rules.json     # 意图检测规则
│   │   ├── mcp_servers.json      # MCP 服务配置
│   │   └── prompts.yaml          # 系统提示词
│   ├── agent.py                  # Agent 核心循环 + 流式处理
│   ├── agent_logger.py           # 会话日志记录器
│   ├── approval_core.py          # 审批流程管理器
│   ├── config.py                 # 全局配置
│   ├── erp_client.py             # ERP 客户端封装
│   ├── errors.py                 # 统一错误模型
│   ├── intent_detector.py        # 意图检测引擎
│   ├── llm.py                    # LLM 调用封装
│   ├── main.py                   # FastAPI 入口 + API 路由
│   ├── prompt_config.py          # 提示词配置加载
│   └── requirements.txt          # Python 依赖
│
├── erp_app/                      # 本地 ERP 业务模块
│   ├── services/                 # 业务服务层
│   │   ├── inventory_service.py  # 库存服务
│   │   ├── order_service.py      # 订单服务
│   │   └── supplier_service.py   # 供应商服务
│   ├── approval_detail.py        # 审批详情生成
│   ├── config.py                 # ERP 配置
│   ├── db.py                     # SQLite 数据库
│   ├── errors.py                 # ERP 错误定义
│   ├── main.py                   # ERP API 路由
│   ├── models.py                 # 数据模型
│   ├── schemas.py                # Pydantic Schema
│   ├── seed.py                   # 种子数据
│   ├── tools.py                  # 工具定义 + 注册表
│   └── tools_format.py           # 工具格式化
│
├── erp_mcp_service/              # MCP 协议服务
│   ├── approval_manager.py       # MCP 审批管理
│   ├── config.py                 # MCP 服务配置
│   ├── main.py                   # MCP 服务入口（JSON-RPC）
│   ├── session_manager.py        # 会话管理
│   ├── task_manager.py           # 异步任务管理
│   ├── tools.py                  # MCP 工具定义
│   └── requirements.txt          # MCP 服务依赖
│
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── App.jsx               # 应用入口
│   │   ├── ChatPage.jsx          # 主聊天页面
│   │   ├── ApprovalCard.jsx      # 审批卡片组件
│   │   ├── StreamingMessage.jsx  # 流式消息组件
│   │   ├── DataVizCard.jsx       # 数据可视化卡片
│   │   ├── McpErrorNotification.jsx # MCP 错误通知
│   │   ├── ThinkingIndicator.jsx # 思考指示器
│   │   ├── ToolStatusCard.jsx    # 工具状态卡片
│   │   ├── SessionManager.js     # 会话管理逻辑
│   │   ├── useStreamingChat.js   # 流式聊天 Hook
│   │   └── httpUtils.js          # HTTP 请求工具
│   ├── .default.env              # 默认环境变量
│   ├── .development.env          # 开发环境变量
│   ├── package.json              # 前端依赖
│   └── vite.config.js            # Vite 配置
│
├── docs/                         # 文档
├── issues/                       # 问题追踪
├── openspec/                     # 变更管理
├── logs/                         # 运行日志
├── .default.env                  # 全局默认环境变量
└── README.md                     # 项目说明
```

---

## 三、核心模块详解

### 3.1 Agent 核心（app/agent.py）

Agent 核心是整个系统的中枢，负责 LLM 交互、工具调用、风险路由和审批流程。

**核心流程：**

```
用户消息 + 历史上下文
       ↓
  build_messages() 构建消息列表
       ↓
  call_llm() 调用 LLM
       ↓
  ┌─ finish_reason=stop ─→ 意图检测 ─→ 需要工具? ─→ _force_tool_retry()
  │                                        ↓ 否
  │                                   直接返回回复
  └─ finish_reason=tool_calls ─→ _handle_tool_calls()
                                       ↓
                              ┌─ SAFE ──→ 直接执行
                              ├─ CAUTION → 限额检查 → 执行
                              └─ DANGER ─→ 创建审批 → 返回 pending_action
```

**双模式支持：**

| 方法 | 说明 |
|------|------|
| `chat()` | 同步模式，一次性返回完整结果 |
| `stream_chat()` | 流式模式，通过 SSE 逐步推送事件 |

**SSE 事件类型：**

| 事件 | 数据 | 说明 |
|------|------|------|
| `thinking` | `{stage, message}` | 思考状态 |
| `tool_call` | `{tool, args, status}` | 工具调用开始 |
| `tool_result` | `{tool, result, status}` | 工具执行结果 |
| `reply_chunk` | `{content}` | 回复文本片段 |
| `done` | `{complete, tool_calls, pending_action}` | 流结束 |

### 3.2 审批核心（app/approval_core.py）

管理高风险操作的审批生命周期。

**审批状态机：**

```
PENDING ──→ 用户确认 ──→ approved=True ──→ 执行工具
   │
   ├──→ 用户拒绝 ──→ approved=False ──→ 返回"操作已取消"
   │
   └──→ TTL过期 ──→ cleanup_expired() ──→ 返回"操作已过期"
```

**关键配置：**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APPROVAL_TTL` | 300秒 | 审批超时时间 |
| `APPROVAL_MAX_PENDING` | 10 | 最大待审批数 |

### 3.3 客户端工厂（app/clients/client_factory.py）

工具路由的核心调度器，统一管理本地适配器和 MCP 客户端。

**路由策略：**

```
工具调用请求
    ↓
检查 MCP 工具别名映射 (mcp_tool_alias)
    ↓
查找工具所属客户端 (tool_prefix_map)
    ↓
┌─ 找到 MCP 客户端 → MCP 客户端执行
├─ 未找到 + 本地适配器启用 → 本地适配器执行
└─ 未找到 + 本地适配器禁用 → TOOL_NOT_FOUND 错误
```

### 3.4 MCP 客户端（app/clients/mcp_client.py）

实现 MCP（Model Context Protocol）协议客户端，通过 JSON-RPC 2.0 与远程 MCP 服务通信。

**协议流程：**

```
1. initialize ──→ 握手 + 协议版本协商
2. notifications/initialized ──→ 通知服务端初始化完成
3. tools/list ──→ 获取可用工具列表
4. tools/call ──→ 调用工具
```

**错误处理：**

| 错误码 | 说明 |
|--------|------|
| `MCP_SERVICE_UNAVAILABLE` | 服务不可用 (503) |
| `MCP_CONNECTION_TIMEOUT` | 连接超时 |
| `MCP_INVALID_RESPONSE` | 响应异常 |
| `MCP_TOOL_NOT_FOUND` | 工具不存在 |
| `MCP_AUTH_FAILED` | 认证失败 (401) |

### 3.5 MCP 注册中心（app/clients/mcp_registry.py）

管理多个 MCP 服务的注册、发现和热重载。

**功能：**
- 从 `mcp_servers.json` 加载服务配置
- 启动时健康检查
- 运行时热重载（`/api/mcp/reload`）
- 线程安全的客户端管理

### 3.6 MCP 服务（erp_mcp_service/）

独立的 MCP 协议服务端，提供标准 JSON-RPC 2.0 接口。

**核心组件：**

| 组件 | 说明 |
|------|------|
| `main.py` | 服务入口 + JSON-RPC 路由分发 |
| `session_manager.py` | 会话生命周期管理 |
| `task_manager.py` | 异步任务（长时间工具调用） |
| `approval_manager.py` | MCP 侧审批管理 |
| `tools.py` | 工具定义与执行 |

**支持的 JSON-RPC 方法：**

| 方法 | 说明 |
|------|------|
| `initialize` | 协议握手 |
| `notifications/initialized` | 初始化通知 |
| `tools/list` | 列出工具 |
| `tools/call` | 调用工具（支持 task 异步模式） |
| `tasks/status` | 查询任务状态 |
| `tasks/complete` | 获取任务结果 |
| `tasks/cancel` | 取消任务 |
| `tasks/list` | 列出任务 |

**响应模式：**

| 模式 | 说明 |
|------|------|
| `json` | 直接返回 JSON |
| `sse` | Server-Sent Events 流式返回 |
| `auto`（默认） | 根据 Accept 头自动选择 |

### 3.7 意图检测（app/intent_detector.py）

防止 LLM 幻觉绕过工具调用的安全机制。

**工作流程：**

```
LLM 返回无 tool_calls
    ↓
detect_tool_intent() 检测用户消息
    ↓
匹配到操作意图? ──→ 是 ──→ _force_tool_retry() 二次调用
    ↓ 否
普通问答放行
```

**规则配置：** 从 `config_dir/intent_rules.json` 加载，支持环境变量覆盖路径。

### 3.8 本地 ERP（erp_app/）

基于 SQLite 的轻量 ERP 数据层，提供订单、库存、供应商管理。

**数据模型：**

| 实体 | 关键字段 | 状态流转 |
|------|---------|---------|
| Order | order_id, type, status, items, total | pending→shipping→delivered / pending→cancelled |
| Inventory | sku, qty, reserved, available | reserve / release / adjust |
| Supplier | supplier_id, name, contact | - |

**工具注册表：**

| 工具 | 风险级别 | 说明 | 限额 |
|------|---------|------|------|
| `query_order` | SAFE | 查询单个订单 | - |
| `query_orders` | SAFE | 批量查询订单 | 最多10个 |
| `query_inventory` | SAFE | 查询库存 | - |
| `query_supplier` | SAFE | 查询供应商 | - |
| `create_order` | CAUTION | 创建订单 | 最多5项 |
| `update_order` | DANGER | 修改订单 | 需审批 |
| `cancel_order` | DANGER | 取消订单 | 需审批 |
| `delete_order` | DANGER | 删除订单 | 需审批,不可逆 |
| `adjust_inventory` | DANGER | 调整库存 | 需审批 |

---

## 四、前端架构

### 4.1 组件结构

```
App
 └── ChatPage
      ├── 侧边栏
      │   ├── 新建会话按钮
      │   └── 会话列表（删除）
      ├── McpErrorNotification     # MCP 错误通知
      ├── 聊天头部（模式切换）
      ├── 消息列表
      │   └── MessageBubble
      │        ├── 文本内容
      │        ├── ToolStatusCard   # 工具调用记录
      │        ├── ApprovalCard     # 审批卡片
      │        └── StreamingMessage # 流式消息
      ├── 快捷命令栏
      └── 输入区域
```

### 4.2 状态管理

使用 React 内置 `useState` + `useCallback`，无第三方状态库。

**会话持久化：** localStorage 存储完整会话数据。

```javascript
// 会话结构
{
  id: "sess_timestamp_random",
  title: "自动标题",
  createdAt: "ISO时间",
  messages: [
    {
      role: "user" | "assistant",
      content: string,
      timestamp: string,
      toolCalls: [],
      pendingActions: [],
      approvalStates: [],
      // 流式消息额外字段
      isStreaming: boolean,
      isDone: boolean,
      replyContent: string,
      toolEvents: [],
      thinkingState: object | null
    }
  ]
}
```

### 4.3 通信模式

| 模式 | API | 说明 |
|------|-----|------|
| 同步 | `POST /chat` | 一次性返回完整结果 |
| 流式 | `POST /chat/stream` | SSE 逐步推送 |
| 审批确认 | `POST /chat/confirm` | 确认/拒绝审批 |

---

## 五、API 接口

### 5.1 聊天接口

**POST /chat**

```json
// 请求
{ "message": "查询订单123", "history": [...], "session_id": "sess_xxx" }

// 响应
{
  "reply": "订单123当前状态: 运输中",
  "tool_calls": [{"tool": "query_order", "args": {...}, "result": {...}}],
  "pending_action": null,
  "error": null
}
```

**POST /chat/stream** — SSE 流式响应

**POST /chat/confirm**

```json
// 请求
{ "action_id": "act_xxx", "approved": true, "history": [...], "session_id": "sess_xxx" }

// 响应（确认）
{ "reply": "地址已修改", "tool_calls": [...], "pending_action": null, "error": null }

// 响应（拒绝）
{ "reply": "操作已取消", "tool_calls": [], "pending_action": null, "error": null }
```

### 5.2 MCP 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/mcp/reload` | POST | 热重载 MCP 服务配置 |
| `/api/mcp/debug` | GET | 查看 MCP 注册状态 |
| `/health` | GET | 健康检查 |

### 5.3 MCP 协议接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/mcp` | POST | JSON-RPC 统一入口 |
| `/mcp` | GET | SSE 长连接 |
| `/health` | GET | MCP 服务健康检查 |

---

## 六、错误体系

### 6.1 五层错误模型

| 层级 | 错误码 | 说明 |
|------|--------|------|
| LLM | `LLM_TIMEOUT` / `LLM_OVERLOAD` / `LLM_TOKEN_LIMIT` / `LLM_INVALID_RESPONSE` / `LLM_RETRY_EXHAUSTED` | AI 服务异常 |
| TOOL | `TOOL_NOT_FOUND` / `TOOL_MISSING_PARAM` / `TOOL_INVALID_PARAM` / `TOOL_LIMIT` / `TOOL_EXPIRED` | 工具调用异常 |
| APPROVAL | `APPROVAL_FAILED` / `APPROVAL_REQUIRED` | 审批流程异常 |
| DATA | `DATA_NOT_FOUND` / `DATA_INSUFFICIENT` / `DATA_CONFLICT` / `DATA_INVALID_SUPPLIER` | 数据层异常 |
| MCP | `MCP_SERVICE_UNAVAILABLE` / `MCP_CONNECTION_TIMEOUT` / `MCP_INVALID_RESPONSE` / `MCP_TOOL_NOT_FOUND` / `MCP_AUTH_FAILED` | MCP 服务异常 |

### 6.2 错误结构

```json
{
  "code": "DATA_NOT_FOUND",
  "message": "未找到订单123的记录",
  "detail": "订单 '123' not found",
  "source": "data",
  "recoverable": true
}
```

---

## 七、安全机制

### 7.1 双层验证

```
节点1: 工具调用验证
  LLM 返回无 tool_calls → detect_tool_intent() → _force_tool_retry()

节点2: 审批流程验证
  DANGER 工具 → create_pending() → 失败返回 APPROVAL_FAILED
  函数末尾 → has_danger 且无 pending_action → APPROVAL_REQUIRED
```

### 7.2 MCP 认证

MCP 服务支持 API Key 认证（`MCP_API_KEY` 环境变量），通过 `X-API-Key` 请求头验证。

---

## 八、配置清单

### 8.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | LLM API 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 端点 |
| `LLM_MODEL` | `gpt-3.5-turbo` | 模型选择 |
| `BACKEND_PORT` | `9000` | 后端端口 |
| `CLIENT_BACKEND` | `hybrid` | 客户端后端模式 |
| `ENABLE_LOCAL_ADAPTER` | `true` | 启用本地适配器 |
| `MCP_SERVICE_URL` | - | MCP 服务地址 |
| `APPROVAL_TTL` | `300` | 审批超时(秒) |
| `APPROVAL_MAX_PENDING` | `10` | 最大待审批数 |
| `HISTORY_WINDOW_N` | `6` | 上下文窗口轮数 |
| `LLM_TIMEOUT` | `15` | LLM 调用超时(秒) |
| `MCP_REQUEST_TIMEOUT` | `10` | MCP 请求超时(秒) |
| `MCP_CONNECT_TIMEOUT` | `5` | MCP 连接超时(秒) |
| `SSE_PING_INTERVAL` | `15` | SSE 心跳间隔(秒) |
| `SSE_TIMEOUT` | `60` | SSE 超时(秒) |
| `INTENT_RULES_PATH` | `app/config/intent_rules.json` | 意图规则路径 |
| `MCP_SERVICE_PORT` | `9001` | MCP 服务端口 |
| `MCP_API_KEY` | - | MCP 服务 API Key |
| `MCP_RESPONSE_MODE` | `auto` | MCP 响应模式 |

### 8.2 前端环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_PORT` | `9000` | 后端 API 端口 |

---

## 九、部署方式

```bash
# 后端
pip install -r app/requirements.txt
python -m app.main                    # 启动 Agent 后端 (端口 9000)

# MCP 服务（可选）
pip install -r erp_mcp_service/requirements.txt
python -m erp_mcp_service.main        # 启动 MCP 服务 (端口 9001)

# 前端
cd frontend && npm install && npm run dev  # Vite 开发服务器
```

---

## 十、数据流

### 10.1 同步聊天流程

```
用户输入 → ChatPage.handleSyncSend()
  → httpUtils.chatPost() → POST /chat
  → agent.chat() → build_messages() → call_llm()
  → _handle_tool_calls() → ClientFactory.execute_tool()
  → ERP Adapter / MCP Client → 返回结果
  → _generate_reply_from_results() → call_llm() 生成回复
  → ChatResponse → 前端渲染
```

### 10.2 流式聊天流程

```
用户输入 → ChatPage.handleStreamSend()
  → useStreamingChat.startStream()
  → httpUtils.chatStreamReader() → POST /chat/stream
  → agent.stream_chat() → SSE 事件流
  → onThinking / onToolCall / onReplyChunk / onDone
  → 前端实时渲染
```

### 10.3 审批流程

```
DANGER 工具 → approval_core.create_pending()
  → 返回 pending_action → 前端展示 ApprovalCard
  → 用户确认 → POST /chat/confirm
  → approval_core.confirm() → ClientFactory.execute_tool()
  → _generate_reply_from_results() → 返回结果
```

---

## 十一、扩展路线

| 阶段 | 内容 |
|------|------|
| Phase 2 | PostgreSQL 持久化 + LangGraph 状态机 |
| Phase 3 | 真实 ERP 适配器 (SAP/Odoo) |
| Phase 4 | 权限系统 (RBAC) |
| Phase 5 | 工作流引擎 + 审批流 |
| Phase 6 | RAG 知识库 |
