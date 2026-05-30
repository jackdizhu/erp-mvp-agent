# ERP Agent MVP 设计方案

> **基于大模型的 ERP 操作型 Agent 系统（MVP）**
> 验证"AI是否可以稳定驱动ERP操作闭环"

---

# 一、项目定位

## 1.1 产品定义

通过自然语言驱动 ERP 操作，支持查询、写入、批处理，以及基于风险分级的审批确认流程。

**核心能力:**
- 自然语言驱动 ERP 操作
- LLM 原生 Tool Calling 执行业务逻辑
- 三级风险路由（SAFE/CAUTION/DANGER）
- 副作用操作审批确认机制
- 会话上下文管理（前端持久化 + 历史窗口）

## 1.2 本质抽象

```
User（自然语言）
   ↓
LLM（意图识别 + Tool选择）
   ↓
Tool Layer（ERP能力封装 + 风险路由）
   ↓
Mock ERP（数据层 + 状态机）
```

## 1.3 MVP目标

只验证一件事：**"AI是否可以稳定驱动ERP操作闭环"**

## 1.4 非目标（明确砍掉）

- 工作流引擎
- 多ERP真实集成
- 权限系统
- RAG知识库
- 流式UI
- RPA自动化
- 微服务架构

---

# 二、系统架构设计

## 2.1 总体架构

```
[ React Frontend (Vite) ]
        ↓ HTTP
[ FastAPI Backend ]
        ↓
[ Agent Core (风险路由) ]
        ↓
[ LLM (Tool Calling API) ]
        ↓
[ Tool Layer (9个ERP工具) ]
        ↓
[ Mock ERP Data Store ]
```

## 2.2 架构原则

- 单体后端（避免复杂度）
- Tool Calling 是唯一扩展机制
- ERP 先 mock，后扩展真实系统
- 前端只负责 UI 展示和状态持久化

---

# 三、技术选型

## 3.1 前端

| 技术 | 是否使用 | 说明 |
|------|---------|------|
| React + Vite | 必须 | UI框架 |
| 状态管理 | 内置 | useState/useCallback |
| UI库 | 不用 | 原生CSS |
| 持久化 | localStorage | 会话数据本地存储 |

## 3.2 后端

| 技术 | 是否使用 | 说明 |
|------|---------|------|
| FastAPI | 必须 | API服务 |
| Python | 必须 | Agent逻辑 |
| Pydantic | 必须 | 数据验证 |
| PostgreSQL | 暂不用 | MVP阶段内存数据 |

## 3.3 AI层

| 技术 | 是否使用 | 说明 |
|------|---------|------|
| LLM API | 必须 | OpenAI兼容接口 |
| OpenAI SDK | 必须 | Python SDK调用 |
| LangGraph | 暂不用 | 后期增强 |

---

# 四、核心模块设计

## 4.1 前端模块

### 页面结构

```
ChatPage (唯一页面)
├── 侧边栏 (SessionManager)
│   ├── 新建会话
│   ├── 会话列表
│   └── 删除会话
├── 聊天区域
│   ├── 消息列表
│   │   ├── 用户消息
│   │   └── 助手消息
│   │       ├── 文本回复
│   │       ├── 工具调用记录
│   │       └── 审批卡片 (ApprovalCard)
│   └── 输入区域
│       ├── 文本输入
│       └── 发送按钮
```

### 前端逻辑

```
用户输入
→ 本地添加用户消息 (localStorage持久化)
→ POST /chat (携带最近6轮历史)
→ 返回 reply + tool_calls + pending_action
→ 渲染助手消息 + 审批卡片(如有)
→ 用户确认/拒绝
→ POST /chat/confirm
→ 返回执行结果
```

## 4.2 后端模块

### 目录结构

```
/app
  main.py        # FastAPI入口 + CORS + Pydantic模型
  agent.py       # Agent核心循环 + 风险路由
  tools.py       # 9个ERP工具定义 + 注册表 + 执行器
  llm.py         # LLM调用封装 (OpenAI兼容)
  mock_erp.py    # Mock ERP数据 + 状态机
  approval.py    # 审批流程管理器 (TTL过期)
  config.py      # 风险级别 + 限额 + 配置
  errors.py      # 统一错误模型 (4层)
```

### Agent核心逻辑

```
用户消息 + 历史上下文
   ↓
LLM判断是否需要Tool
   ↓
【风险路由】
   SAFE → 直接执行
   CAUTION → 限额检查后执行
   DANGER → 创建待审批动作, 暂存不执行
   ↓
SAFE/CAUTION结果 → 回传LLM生成回复
DANGER动作 → 返回pending_action给前端
   ↓
前端展示审批卡片
用户确认 → POST /chat/confirm → 执行Tool → LLM生成回复
用户拒绝 → 返回取消消息
```

## 4.3 Chat API

### POST /chat

**输入:**
```json
{
  "message": "查询订单123状态",
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "您好,有什么可以帮您的?"}
  ]
}
```

**输出:**
```json
{
  "reply": "订单123当前状态:运输中",
  "tool_calls": [
    {"tool": "query_order", "args": {"order_id": "123"}, "result": {...}}
  ],
  "pending_action": null,
  "error": null
}
```

### POST /chat/confirm

**输入:**
```json
{
  "action_id": "act_xxx",
  "approved": true,
  "history": [...]
}
```

---

# 五、Tool系统设计

## 5.1 工具注册表

| 工具 | 风险级别 | 说明 | 限额 |
|------|---------|------|------|
| query_order | SAFE | 查询单个订单 | - |
| query_orders | SAFE | 批量查询订单 | 最多10个 |
| query_inventory | SAFE | 查询库存 | - |
| query_supplier | SAFE | 查询供应商 | - |
| create_order | CAUTION | 创建订单(含库存预留) | 最多5项 |
| update_order | DANGER | 修改订单字段 | 需审批 |
| cancel_order | DANGER | 取消订单+释放库存 | 需审批 |
| delete_order | DANGER | 删除已取消订单 | 需审批,不可逆 |
| adjust_inventory | DANGER | 调整库存 | 需审批 |

## 5.2 风险路由机制

```python
SAFE工具:
  直接execute_tool()
  结果附加到tool_calls
  回传LLM生成回复

CAUTION工具:
  检查限额 (环境变量配置)
  通过则执行,否则返回错误
  结果附加到tool_calls

DANGER工具:
  approval_manager.create_pending()
  暂存到pending_actions字典
  返回pending_action给前端
  等待用户确认/拒绝
```

## 5.3 审批流程

```
DANGER工具调用
   ↓
生成action_id (act_xxx)
设置TTL (默认300秒)
存储到pending_actions字典
   ↓
前端展示ApprovalCard
   ↓
用户确认 → approval_manager.confirm(action_id, true)
  → 从字典移除
  → execute_tool()
  → LLM生成回复
  → 返回结果

用户拒绝 → approval_manager.confirm(action_id, false)
  → 从字典移除
  → 返回"操作已取消"

超时 → cleanup_expired()
  → 返回"操作已过期"
```

---

# 六、Mock ERP数据层

## 6.1 数据模型

```python
orders = {
  "SO-1001": {
    "order_id": "SO-1001",
    "type": "sales",              # sales/purchase
    "status": "pending",          # pending/shipping/delivered/cancelled
    "customer": "客户A",
    "items": [{"sku": "SKU001", "name": "iPhone 15", "qty": 10, "price": 5999}],
    "total": 59990,
    "address": "北京市朝阳区",
    "created_at": "2024-01-15",
    "updated_at": "2024-01-15",
    "cancel_reason": None,
    "notes": ""
  }
}

inventory = {
  "SKU001": {
    "sku": "SKU001",
    "name": "iPhone 15",
    "qty": 100,                   # 总库存
    "reserved": 10,               # 已预留
    "available": 90,              # 可用库存 (qty - reserved)
    "unit": "台",
    "unit_price": 5999
  }
}

suppliers = {
  "SUP001": {
    "supplier_id": "SUP001",
    "name": "供应商A",
    "contact": "张三",
    "phone": "13800138000"
  }
}
```

## 6.2 状态机

```
订单状态流转:
  pending → shipping → delivered
  pending → cancelled
  cancelled → (删除)

库存操作:
  创建销售订单 → reserve_inventory() (qty增加, available减少)
  取消销售订单 → release_inventory() (qty不变, reserved减少, available增加)
  调整库存 → adjust_inventory() (qty变化, 重新计算available)
```

## 6.3 约束验证

```python
can_transition(order_id, target_status)  # 状态转换合法性
can_mutate(order_id, field)              # 字段修改合法性
recalc_available(sku)                    # 重新计算可用库存
```

---

# 七、错误模型

## 7.1 四层错误体系

```
LLM层:
  LLM_TIMEOUT        - AI服务暂时不可用
  LLM_OVERLOAD       - AI服务繁忙
  LLM_TOKEN_LIMIT    - 请求内容过长
  LLM_INVALID_RESPONSE - AI返回异常

TOOL层:
  TOOL_NOT_FOUND     - 不支持的操作
  TOOL_MISSING_PARAM - 缺少参数
  TOOL_INVALID_PARAM - 参数格式错误
  TOOL_LIMIT         - 超出限额
  TOOL_EXPIRED       - 审批过期

DATA层:
  DATA_NOT_FOUND     - 未找到记录
  DATA_INSUFFICIENT  - 库存不足
  DATA_CONFLICT      - 状态冲突
  DATA_INVALID_SUPPLIER - 供应商不存在

SYSTEM层:
  SYS_TIMEOUT        - 请求超时
  SYS_ERROR          - 系统异常
```

## 7.2 错误结构

```json
{
  "code": "DATA_NOT_FOUND",
  "message": "未找到订单123的记录",
  "detail": "订单 '123' not found",
  "source": "data",
  "recoverable": true
}
```

## 7.3 可恢复性标记

- `recoverable: true` - 用户可重试
- `recoverable: false` - 需修改请求或联系管理员

---

# 八、会话管理

## 8.1 前端持久化

```javascript
// localStorage存储
localStorage.setItem("erp_agent_sessions", JSON.stringify(sessions))

// 会话结构
{
  id: "sess_timestamp_random",
  title: "新会话 / 自动标题",
  createdAt: "ISO时间",
  messages: [
    {role, content, timestamp, pendingActions, approvalStates}
  ]
}
```

## 8.2 历史窗口

```python
# 默认截取最近6轮
HISTORY_WINDOW = {"default_n": 6}

def truncate_history(messages, n=6):
  if len(messages) <= n:
    return messages
  return messages[-n:]
```

## 8.3 深层拷贝机制

```javascript
// 确保React状态不可变更新
setSessions(prev => {
  const updated = updater([
    ...prev.map(s => ({...s, messages: [...s.messages]}))
  ]);
  return updated;
});
```

---

# 九、MVP验证场景

## 场景1：订单查询

```
输入: "订单123现在什么状态?"
路由: SAFE → query_order("123")
输出: "订单123当前状态:运输中,预计6月1日送达。"
```

## 场景2：创建采购订单

```
输入: "为供应商A创建采购订单:iPhone 15 ×10"
路由: CAUTION → 限额检查 → create_order()
输出: "采购订单已创建:PO-1001"
```

## 场景3：库存判断+推理

```
输入: "iPhone 15还有库存吗?能接100台订单吗?"
路由: SAFE → query_inventory("iPhone 15")
输出: "当前库存60台,不足100台,建议拆单或补货。"
```

## 场景4：异常订单处理

```
输入: "订单124为什么还没发货?"
路由: SAFE → query_order("124")
输出: "订单124未发货原因:库存不足,等待补货。"
```

## 场景5：批量查询

```
输入: "查一下订单123、124、125状态"
路由: SAFE → query_orders(["123","124","125"])
输出: "123:运输中  124:待发货  125:已签收"
```

## 场景6：修改订单(审批)

```
输入: "把订单123的收货地址改成北京市朝阳区"
路由: DANGER → approval_manager.create_pending()
前端: 展示审批卡片
用户确认: → update_order() → "地址已修改"
```

## 场景7：取消订单(审批)

```
输入: "取消订单124"
路由: DANGER → approval_manager.create_pending()
前端: 展示审批卡片
用户确认: → cancel_order() → release_inventory() → "订单已取消,库存已释放"
```

---

# 十、部署方式

```bash
# 后端
cd app
pip install -r requirements.txt
python -m main              # uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev                 # Vite dev server

# 同时启动
./start.sh
```

**无需:** Docker / K8s / CI/CD / Nginx

---

# 十一、配置清单

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| OPENAI_API_KEY | - | LLM API密钥 |
| OPENAI_BASE_URL | https://api.openai.com/v1 | 自定义API端点 |
| LLM_MODEL | gpt-3.5-turbo | 模型选择 |
| APPROVAL_TTL | 300 | 审批超时(秒) |
| APPROVAL_MAX_PENDING | 10 | 最大待审批数 |
| HISTORY_WINDOW_N | 6 | 上下文窗口大小 |
| TOOL_LIMIT_CREATE | 5 | 创建订单最大数量 |
| TOOL_LIMIT_UPDATE | 5 | 修改订单最大数量 |
| TOOL_LIMIT_BATCH | 10 | 批量查询最大数量 |

---

# 十二、扩展路线

| 阶段 | 内容 |
|------|------|
| Phase 2 | PostgreSQL持久化 + LangGraph状态机 |
| Phase 3 | 真实ERP适配器(SAP/Odoo) |
| Phase 4 | 权限系统(RBAC) |
| Phase 5 | 工作流引擎 + 审批流 |
| Phase 6 | RAG知识库 |

---

# 十三、核心设计总结

## 1. Agent本质

```
LLM + Tool Router + 风险路由
```

## 2. ERP本质

```
数据 + 操作接口 + 状态机
```

## 3. MVP本质

```
验证闭环,不做工程化
```

## 4. 成功标准

- 能问订单
- 能调用工具
- 能返回ERP结果
- 能处理审批流程

**满足以上4点,MVP即成功**
