## Context

当前项目中存在两种工具格式：

| 模块 | 当前格式 | 来源 |
|------|----------|------|
| `erp_app/tools.py` | OpenAI function calling | `TOOL_SCHEMAS` |
| `erp_mcp_service/tools.py` | MCP 原生格式 | `list_tools()` 返回 |
| `app/clients/mcp_client.py` | MCP 原生格式 | 工具解析 |

VS Code MCP 扩展只接受 MCP 原生格式，但项目核心使用的是 OpenAI 格式。

## Goals / Non-Goals

**Goals:**
- 统一整个项目使用 MCP 原生工具格式
- 移除格式转换层，简化代码
- 保持工具功能不变

**Non-Goals:**
- 不改变工具数量和功能
- 不改变工具参数定义
- 不改变现有的业务逻辑

## Decisions

### 1. 新工具格式定义

**Decision**: 使用 MCP 原生格式作为统一格式

```json
{
  "name": "query_order",
  "description": "根据订单ID查询订单详情",
  "inputSchema": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "string",
        "description": "订单编号"
      }
    },
    "required": ["order_id"]
  }
}
```

**Rationale**: MCP 原生格式是行业标准，得到 VS Code MCP 扩展支持。

### 2. erp_app/tools.py 重构

**Decision**: 重写 `TOOL_SCHEMAS` 为 MCP 原生格式

**Rationale**: 单一格式定义，消除转换需求。

### 3. MCP Client 适配

**Decision**: `mcp_client.py` 保持解析 MCP 原生格式

**Rationale**: MCP 客户端本来就期望 MCP 格式，无需修改。

## 工具格式对比

| 字段 | OpenAI 格式 | MCP 原生格式 |
|------|-------------|--------------|
| 工具名称 | `function.name` | `name` |
| 描述 | `function.description` | `description` |
| 参数定义 | `function.parameters` | `inputSchema` |

## 迁移计划

1. 修改 `erp_app/tools.py` 的 `TOOL_SCHEMAS`
2. 验证 `erp_mcp_service/tools.py` 直接使用新格式
3. 验证 `app/clients/mcp_client.py` 解析正确
4. 测试 VS Code MCP 扩展工具列表

## Open Questions

- 本地 `erp_adapter` 使用相同工具格式，是否需要同步更新？
- 是否有其他客户端依赖 OpenAI 格式？