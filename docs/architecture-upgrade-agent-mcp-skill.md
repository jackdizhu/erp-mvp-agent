# ERP Agent 架构升级：Agent / MCP / Skill 三层配置体系

## 1. 背景与目标

当前架构为 **单 Agent + 单 MCP + 硬编码工具** 的紧耦合模式，所有配置集中在 `app/config_dir/` 目录下，无法支持多智能体、多 MCP 服务、可扩展 Skill 能力。

### 升级目标

- 新增 `agent/`、`mcp/`、`skills/` 三个顶层配置目录
- 每个 Agent 搭配预设的 MCP 和 Skills，同时支持扩展
- 用户可创建自定义 Skill（仅 Markdown 工作流描述，无代码执行）
- Agent 按会话绑定：新会话初始化时选择 Agent，会话内不可切换
- 迁移现有 `config_dir/` 配置到新目录

---

## 2. 目录结构

```
erp-mvp-agent/
├── agent/                          ← 智能体配置
│   ├── erp.yaml                    ← ERP 智能体（从 config_dir 迁移）
│   └── _schema.yaml                ← agent 配置 Schema
│
├── mcp/                            ← MCP 客户端配置
│   ├── erp.json                    ← ERP MCP 服务（从 config_dir 迁移）
│   └── _schema.json                ← MCP 配置 Schema
│
├── skills/                         ← Skill 能力
│   ├── order/                      ← 预设 skill：订单管理
│   │   ├── skill.yaml              ← 元数据 + prompt + 工作流定义
│   │   └── handler.py              ← Python 工作流编排逻辑
│   ├── inventory/                  ← 预设 skill：库存管理
│   │   ├── skill.yaml
│   │   └── handler.py
│   ├── supplier/                   ← 预设 skill：供应商管理
│   │   ├── skill.yaml
│   │   └── handler.py
│   └── custom/                     ← 用户自定义 skill
│       └── {skill_name}/
│           ├── skill.yaml          ← 元数据
│           └── workflow.md         ← Markdown 工作流描述（无代码）
│
├── app/                            ← 现有代码 + 新增运行时模块
│   ├── skills/                     ← 新增：Skill 运行时
│   │   ├── __init__.py
│   │   ├── loader.py               ← SkillLoader（扫描+加载）
│   │   ├── executor.py             ← SkillExecutor（执行工作流）
│   │   ├── workflow_parser.py      ← 解析 workflow.md
│   │   └── base.py                 ← SkillHandler 基类
│   ├── agent_runtime.py            ← 新增：Agent 运行时
│   ├── config_dir/                 ← 保留，标记 deprecated，兼容旧启动
│   └── ...
└── ...
```

---

## 3. 配置 Schema

### 3.1 agent/erp.yaml

从 `prompts.yaml` + `intent_rules.json` 迁移升级：

```yaml
name: erp
version: "1.0"
description: "ERP智能助手"

prompt:
  role: "你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。"
  capabilities_header: "你可以执行以下操作："
  capabilities_footer: ""
  risk_notice: "对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。"
  response_style: "请用简洁专业的中文回复用户。"

# 预设 MCP 服务
preset_mcp:
  - erp

# 预设 Skill
preset_skills:
  - order
  - inventory
  - supplier

# 扩展 MCP（用户追加）
extra_mcp: []

# 扩展 Skill（用户追加，含 custom）
extra_skills: []

# 意图检测规则（从 intent_rules.json 迁移）
intent_rules:
  update_order:
    zh: ["修改.*订单", "改.*地址", "改.*电话", "更新.*订单", "变更.*订单", "订单.*改为", "地址.*改成", "电话.*改成"]
    en: ["update.*order", "change.*address", "modify.*order", "edit.*order", "order.*to", "address.*to", "phone.*to"]
  cancel_order:
    zh: ["取消.*订单", "不要.*订单", "退掉.*订单", "订单.*取消", "撤销.*订单", "作废.*订单"]
    en: ["cancel.*order", "delete.*order", "remove.*order", "void.*order", "revoke.*order"]
  delete_order:
    zh: ["删除.*订单", "删掉.*订单", "移除.*订单", "彻底.*删除"]
    en: ["delete.*order", "remove.*order.*permanently", "purge.*order"]
  adjust_inventory:
    zh: ["调整.*库存", "修改.*库存", "增加.*库存", "减少.*库存", "库存.*加", "库存.*减", "补货", "入库", "出库"]
    en: ["adjust.*inventory", "update.*stock", "add.*stock", "increase.*inventory", "decrease.*inventory", "restock", "stock.*in", "stock.*out"]
```

### 3.2 mcp/erp.json

从 `mcp_servers.json` 迁移，扁平结构（一个文件一个 MCP 服务）：

```json
{
  "name": "erp",
  "url": "http://localhost:9001",
  "type": "streamableHttp",
  "headers": {
    "Accept": "application/json, text/event-stream",
    "X-API-Key": "mcp-erp-agent-550e8400-e29b-41d4-a716-446655440000"
  },
  "timeout": 30
}
```

> 关键变化：从 `{"mcpServers": {"erp": {...}}}` 嵌套结构变为扁平结构。

### 3.3 skills/order/skill.yaml（预设 Skill）

```yaml
name: order
version: "1.0"
description: "订单管理能力"
category: preset

# Skill 提供的工具（来自 MCP 已注册工具）
tools:
  - query_orders
  - create_order
  - update_order
  - cancel_order
  - delete_order

# 注入到 system prompt 的片段
prompt_fragment: |
  订单管理说明：
  - 创建订单时需提供客户信息和商品列表
  - 修改订单最多支持5个商品项
  - 取消订单需确认

# 工作流编排定义
workflows:
  batch_import:
    description: "批量导入订单"
    steps:
      - id: parse
        tool: parse_file
        input: "$.file_content"
        output: parsed_data
      - id: validate
        handler: validate_orders
        input: "$.parsed_data"
        output: validated_orders
      - id: create
        tool: create_order
        input: "$.validated_orders[*]"
        output: results
        iterate: true
```

### 3.4 skills/custom/{name}/skill.yaml（用户自定义 Skill）

```yaml
name: batch_query
version: "1.0"
description: "批量查询订单状态"
category: custom

# 只能引用当前 agent MCP 已注册的工具
tools:
  - query_orders

prompt_fragment: |
  批量查询说明：根据订单号列表逐个查询并汇总

# 自定义 skill 无 workflows 字段，工作流定义在 workflow.md 中
```

### 3.5 skills/custom/{name}/workflow.md（用户工作流描述）

```markdown
# 批量查询订单状态

## 描述
根据订单号列表，逐个查询订单状态并汇总结果

## 步骤

### 1. 解析输入
- 类型: prompt
- 指令: 从用户消息中提取所有订单号，返回 JSON 数组

### 2. 逐条查询
- 类型: tool_call
- 工具: query_orders
- 参数: {"order_id": "{{step1.items[*].order_id}}"}
- 迭代: true
- 输出: order_results

### 3. 汇总回复
- 类型: prompt
- 指令: 将查询结果整理为表格格式回复用户
```

---

## 4. 运行时架构

### 4.1 启动流程

```
main.py startup
       │
       ▼
  ┌─────────────┐
  │ AgentLoader │──→ 扫描 agent/*.yaml，注册所有可用 agent
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐     ┌─────────────┐
  │  MCPLoader  │     │ SkillLoader │
  │             │     │             │
  │ 扫描 mcp/   │     │ 扫描 skills/ │
  │ 注册所有    │     │ 注册所有    │
  │ MCP 配置    │     │ skill 元数据 │
  └──────┬──────┘     └──────┬──────┘
         │                   │
         ▼                   ▼
  ┌──────────────────────────────────────┐
  │         全局注册表（启动时完成）       │
  │                                      │
  │  agent_registry ──→ 所有 agent 配置  │
  │  mcp_configs ──→ 所有 MCP 配置       │
  │  skill_registry ──→ 所有 skill 元数据│
  │                                      │
  │  注意：MCP 连接和 Skill 加载         │
  │  在会话初始化时按 agent 配置按需执行  │
  └──────────────────────────────────────┘
```

### 4.2 会话初始化流程（Agent 按会话绑定）

```
┌─────────────────────────────────────────────────────────────┐
│         会话初始化：选择 Agent → 绑定会话                     │
└─────────────────────────────────────────────────────────────┘

  前端                              后端
   │                                 │
   │  GET /api/agents                │
   │  (列出可用智能体)               │
   │────────────────────────────────▶│
   │  [{name, description,           │
   │    preset_mcp, preset_skills}]  │
   │◀────────────────────────────────│
   │                                 │
   │  用户选择 agent，新开会话        │
   │                                 │
   │  POST /api/session/init         │
   │  {agent_name: "erp"}            │
   │────────────────────────────────▶│
   │                                 │──→ 创建 session_id
   │                                 │──→ 按 agent 配置加载:
   │                                 │     ├── preset_mcp → 建立 MCP 连接
   │                                 │     ├── preset_skills → 加载 Skill
   │                                 │     └── 组装 system prompt
   │                                 │──→ 绑定 session_id ↔ agent
   │  {session_id, agent_name,       │
   │   tools, skills}                │
   │◀────────────────────────────────│
   │                                 │
   │  后续对话携带 session_id        │
   │  会话内 agent 不可切换          │
   │                                 │

  ⚠️ 会话内禁止切换 Agent
  ─────────────────────────
  • 对话过程中 POST /api/agents/{name}/activate → 403 拒绝
  • 切换 Agent 只能通过新开会话实现
  • 前端在对话界面隐藏 Agent 切换入口
```

### 4.3 会话与 Agent 的数据模型

```
┌─────────────────────────────────────────────────────────────┐
│              Session-Agent 绑定关系                           │
└─────────────────────────────────────────────────────────────┘

  Session
  ├── session_id: "sess_abc123"
  ├── agent_name: "erp"              ← 创建时绑定，不可变
  ├── created_at: timestamp
  ├── mcp_clients: [erp_client]      ← 按 agent preset_mcp 初始化
  ├── loaded_skills: [order, inventory, supplier]  ← 按 agent preset_skills
  ├── extra_skills: []               ← 会话内按需加载的 custom skill
  └── system_prompt: "..."           ← 按 agent prompt 组装

  多会话并行：
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Session A    │  │ Session B    │  │ Session C    │
  │ agent: erp   │  │ agent: erp   │  │ agent: readonly│
  │ skills: 3    │  │ skills: 3+1  │  │ skills: 1    │
  └──────────────┘  └──────────────┘  └──────────────┘
       ↑ 不同会话可绑定不同 Agent，互不影响
```

### 4.4 Agent 与 MCP/Skill 的绑定关系

采用 **方案 A 声明式绑定**：agent 配置文件中明确声明依赖的 mcp 和 skill，支持 `extra_*` 扩展。

```
agent/erp.yaml
  ├── preset_mcp: [erp]           ← 会话初始化时加载
  ├── preset_skills: [order, inventory, supplier]  ← 会话初始化时加载
  ├── extra_mcp: []               ← 用户追加的 MCP
  └── extra_skills: []            ← 用户追加的 Skill（含 custom）
```

### 4.5 Custom Skill 按需加载流程（会话内）

```
前端                              后端
 │                                 │
 │  GET /api/skills/available      │
 │  ?session_id=sess_abc123        │
 │  (列出当前会话可加载的 skill)    │
 │────────────────────────────────▶│
 │  [{name, desc, category,        │
 │    status: "unloaded"}]         │
 │◀────────────────────────────────│
 │                                 │
 │  POST /api/skills/load          │
 │  {session_id, skill_name}       │
 │────────────────────────────────▶│
 │                                 │──→ 校验 session 绑定的 agent
 │                                 │──→ SkillLoader.load("custom/xxx")
 │                                 │──→ 校验工具在该 agent MCP 已注册列表中
 │                                 │──→ 注册工具到 session 的 client_factory
 │                                 │──→ 注入 prompt_fragment
 │  {success: true, tools: [...]}  │
 │◀────────────────────────────────│
 │                                 │
 │  (后续对话即可使用新 skill 工具) │
```

### 4.6 Custom Skill 安全校验

```
用户创建 custom skill
       │
       ▼
┌──────────────┐
│  格式校验     │──→ 必须包含 skill.yaml + workflow.md
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  内容校验     │──→ workflow.md 中 tool_call 引用的工具
│              │    必须在当前 agent 的 MCP 已注册工具列表中
│              │──→ 禁止出现文件读写/接口调用/转发关键词
│              │──→ 无 handler.py，不执行任意代码
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  注册到       │──→ skills/custom/{name}/
│  可用列表     │──→ 状态: unloaded（按需加载）
└──────────────┘
```

### 4.7 前端交互流程

```
┌─────────────────────────────────────────────────────────────┐
│              前端页面与 Agent 选择流程                         │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │                   新会话入口                          │
  │                                                      │
  │  ┌─────────────────────────────────────────────┐     │
  │  │  选择智能体                                  │     │
  │  │                                              │     │
  │  │  ┌─────────┐  ┌─────────┐  ┌──────────┐    │     │
  │  │  │  ERP    │  │ 只读查询 │  │  供应商  │    │     │
  │  │  │  助手   │  │  助手   │  │  专员    │    │     │
  │  │  │ ✓ 推荐  │  │         │  │          │    │     │
  │  │  └─────────┘  └─────────┘  └──────────┘    │     │
  │  │                                              │     │
  │  │  已选: ERP助手                               │     │
  │  │  能力: 订单/库存/供应商管理                    │     │
  │  │  MCP: erp                                    │     │
  │  └─────────────────────────────────────────────┘     │
  │                                                      │
  │  ┌──────────┐                                        │
  │  │ 开始对话 │ → POST /api/session/init               │
  │  └──────────┘   {agent_name: "erp"}                  │
  └──────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │                   对话界面                            │
  │                                                      │
  │  ┌─────────────────────────────────────────────┐     │
  │  │  当前会话: ERP助手  │  新开会话 ▼            │     │
  │  │  (不可切换，只能新开)                         │     │
  │  └─────────────────────────────────────────────┘     │
  │                                                      │
  │  ┌─────────────────────────────────────────────┐     │
  │  │  💬 对话区域                                 │     │
  │  │  ...                                        │     │
  │  └─────────────────────────────────────────────┘     │
  │                                                      │
  │  ┌─────────────────────────────────────────────┐     │
  │  │  🛠 可用技能: [订单] [库存] [供应商]         │     │
  │  │  📦 加载更多: [+批量查询] [+自定义...]       │     │
  │  └─────────────────────────────────────────────┘     │
  └──────────────────────────────────────────────────────┘
```

---

## 5. API 端点

### 5.1 会话管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/session/init` | POST | 新建会话并绑定 Agent（必须指定 agent_name） |
| `/api/session/{session_id}` | GET | 获取会话信息（含绑定的 agent、已加载 skills） |
| `/api/session/{session_id}/agent` | GET | 获取会话绑定的 Agent 详情（只读，不可修改） |

### 5.2 Agent 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agents` | GET | 列出可用智能体（供新会话选择） |
| `/api/agents/{name}` | GET | 获取智能体详情（含 preset_mcp、preset_skills） |

### 5.3 Skill 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills/available` | GET | 列出可加载 skill（需传 session_id，按 agent 过滤） |
| `/api/skills/loaded` | GET | 列出指定会话已加载 skill |
| `/api/skills/load` | POST | 按需加载 skill（需传 session_id，校验工具可用性） |
| `/api/skills/unload` | POST | 卸载 skill（需传 session_id） |
| `/api/skills/validate` | POST | 校验 custom skill（创建前预检） |

### 5.4 MCP 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mcp/list` | GET | 列出 MCP 服务 |
| `/api/mcp/reload` | POST | 重载 MCP 配置 |

### 5.5 对话（兼容现有，增加 session_id 必传）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 同步对话（需传 session_id） |
| `/chat/stream` | POST | 流式对话（需传 session_id） |
| `/chat/confirm` | POST | 确认操作（需传 session_id） |

---

## 6. 迁移策略

### Phase 1: 新目录 + 兼容层

- 创建 `agent/`, `mcp/`, `skills/` 目录和配置文件
- 新增 AgentLoader, MCPLoader, SkillLoader
- `main.py` startup 优先读新目录，fallback 到 `config_dir/`
- `config_dir/` 保留不动，零风险

### Phase 2: 迁移数据

- `prompts.yaml` + `intent_rules.json` → `agent/erp.yaml`
- `mcp_servers.json` → `mcp/erp.json`
- 拆分 skill 定义：order, inventory, supplier

### Phase 3: 清理

- `config_dir/` 标记 deprecated
- 删除旧加载逻辑的 fallback 分支

---

## 7. 关键决策记录

| 决策项 | 结论 |
|--------|------|
| Agent 绑定方式 | 方案 A 声明式，agent.yaml 中声明 preset_mcp + preset_skills + extra_* |
| Skill 定位 | 预设 skill 支持 Python 工作流编排；custom skill 仅 Markdown 工作流描述 |
| Custom skill 扩展 | skills/custom/ 目录，按需加载，前端选择后加载 |
| Custom skill 安全 | 仅 Markdown 工作流，禁止代码执行，只能编排已有 MCP tools |
| 工作流执行模型 | 顺序执行 + 迭代，不支持条件分支/并行 |
| Skill-MCP 边界 | 只引用已注册 MCP tools，未注册则报错 |
| 多 Agent 切换 | 按会话绑定，新会话初始化时选择，会话内不可切换 |
| 配置迁移 | prompts.yaml + intent_rules.json → agent/erp.yaml；mcp_servers.json → mcp/erp.json |
