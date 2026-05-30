# Change: tool-call-validation

## Problem

当前 Agent 在处理用户输入时存在以下风险：
1. **LLM 幻觉**：用户输入包含明确操作意图（如"修改订单123地址"），但 LLM 可能直接生成"地址已修改"的回复而未调用 `update_order` 工具
2. **审批绕过**：DANGER 级别工具（update_order/cancel_order/delete_order/adjust_inventory）必须经过审批流程，但 LLM 可能不调用工具导致跳过审批
3. **数据不一致**：用户看到"已修改"的回复，但 Mock ERP 中的数据并未实际变更

这些问题在 MVP 验证阶段可能被忽视，但在生产环境中会导致严重的数据完整性和用户信任问题。

## Goals

1. 确保 LLM 在需要时实际调用 Tool，而非仅生成文本回复
2. 确保所有 DANGER 级别工具调用都经过审批流程
3. 在检测到 LLM 幻觉时，自动进行二次调用并引导 LLM 使用正确的工具
4. 支持中英文用户输入的意图检测，兼容多语言场景

## Non-Goals

- 不修改现有的 Tool 定义和执行逻辑
- 不改变审批流程的基本交互模式
- 不引入新的外部依赖（如 ML 分类模型）
- 不处理 SAFE 和 CAUTION 级别工具的调用验证（仅关注 DANGER 级别）

## Approach

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    CHAT REQUEST FLOW                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  User Message                                           │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────┐                                        │
│  │  LLM Call 1 │ ◄── 带 Tool Schemas                   │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌──────────────────────┐                               │
│  │  节点1: Tool 验证    │                               │
│  │  ─────────────────── │                               │
│  │  有 tool_calls?      │                               │
│  │    ├─ 是 → 继续处理  │                               │
│  │    └─ 否 → 意图检测  │                               │
│  │         ├─ 有意图    │                               │
│  │         │   → LLM Call 2 (引导)  │                   │
│  │         └─ 无意图    │                               │
│  │             → 普通问答放行          │                 │
│  └──────────┬───────────┘                               │
│             │                                           │
│             ▼                                           │
│  ┌──────────────────────┐                               │
│  │  Risk Level Routing  │                               │
│  │  ─────────────────── │                               │
│  │  SAFE   → 直接执行   │                               │
│  │  CAUTION → 限额检查  │                               │
│  │  DANGER → 创建审批   │                               │
│  └──────────┬───────────┘                               │
│             │                                           │
│             ▼                                           │
│  ┌──────────────────────┐                               │
│  │  节点2: 审批验证     │                               │
│  │  ─────────────────── │                               │
│  │  DANGER 工具?        │                               │
│  │    ├─ 是 → 验证      │                               │
│  │    │   pending_action│                               │
│  │    │     存在?       │                               │
│  │    │       ├─ 是 →  │                               │
│  │    │       └─ 否 →  │                               │
│  │    │          拦截错误              │                 │
│  │    └─ 否 → 正常返回  │                               │
│  └──────────┬───────────┘                               │
│             │                                           │
│             ▼                                           │
│  Final Response to Frontend                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. 意图检测引擎 (`app/intent_detector.py`)

```python
INTENT_RULES = {
    "update_order": {
        "zh": ["修改.*订单", "改.*地址", "改.*电话", "更新.*订单"],
        "en": ["update.*order", "change.*address", "modify.*order"]
    },
    "cancel_order": {
        "zh": ["取消.*订单", "不要.*订单", "退掉.*订单"],
        "en": ["cancel.*order", "delete.*order"]
    },
    # ... 其他工具规则
}
```

**工作原理：**
- 用户消息传入 → 正则匹配中英文模式
- 匹配成功 → 返回期望的工具名称
- 无匹配 → 返回 None（普通问答）

#### 2. 工具调用验证（`app/agent.py` - `chat()` 函数）

**现有逻辑：**
```python
if response["finish_reason"] == "stop" or not response["tool_calls"]:
    return {"reply": content, ...}  # 直接放行
```

**新增逻辑：**
```python
if response["finish_reason"] == "stop" or not response["tool_calls"]:
    reply = _strip_think_tags(response["content"]) or ""
    expected_tool = detect_tool_intent(message)
    
    if expected_tool:
        # 强制二次调用
        return _force_tool_retry(messages, message, expected_tool, reply)
    
    return {"reply": reply, ...}
```

#### 3. 审批流程验证（`app/agent.py` - `_handle_tool_calls()` 函数）

**新增检查：**
```python
if has_danger_tools_executed and not pending_action:
    return build_error_response(
        AgentError(
            code="APPROVAL_REQUIRED",
            message="高风险操作需要审批确认",
            ...
        )
    )
```

### 错误码扩展

| 错误码 | 说明 | 可恢复 |
|--------|------|--------|
| `APPROVAL_FAILED` | 审批创建失败 | 否 |
| `APPROVAL_REQUIRED` | 高风险操作未进入审批 | 否 |
| `LLM_RETRY_EXHAUSTED` | LLM 二次调用仍无工具 | 是 |

## Impact

### 文件变更

| 文件 | 变更类型 | 影响范围 |
|------|---------|---------|
| `app/intent_detector.py` | 新增 | 意图检测引擎 |
| `app/agent.py` | 修改 | chat(), _handle_tool_calls() |
| `app/errors.py` | 修改 | 新增 3 个错误码 |
| `app/config.py` | 修改 | INTENT_RULES 配置 |

### API 变更

- **无破坏性变更**：现有 API 响应格式保持不变
- **新增错误场景**：可能返回新的错误码（APPROVAL_REQUIRED, LLM_RETRY_EXHAUSTED）
- **性能影响**：仅在检测到幻觉时增加 1 次 LLM 调用（约 1-2 秒延迟）

### 用户影响

- **正面**：减少 LLM 幻觉导致的数据不一致
- **正面**：高风险操作 100% 进入审批流程
- **中性**：幻觉场景下延迟增加 1-2 秒（可接受）

## Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 关键词误判 | 正常问答被误认为需要工具 | 保守规则，仅匹配明确操作意图 |
| 二次调用仍失败 | 用户收到"无法执行"提示 | 返回友好错误，建议换种表达 |
| 正则性能 | 大量规则影响性能 | 规则数量 < 50，性能可忽略 |
| 多语言覆盖不全 | 部分表达无法检测 | 持续迭代规则，支持用户反馈 |

## Success Criteria

1. **功能验证**：
   - 输入"修改订单123地址" → LLM 必须调用 `update_order` 工具
   - 输入"取消订单124" → 必须创建 `pending_action` 并返回审批卡片
   - 输入"订单123状态" → 正常调用 `query_order`，不触发二次调用

2. **拦截率目标**：
   - DANGER 工具幻觉拦截率 > 95%
   - 误判率 < 5%

3. **性能目标**：
   - 正常场景延迟无影响
   - 幻觉场景额外延迟 < 3 秒
