## Why

VS Code MCP 扩展期望的工具格式是 MCP 原生格式（`{name: ..., inputSchema: ...}`），而当前的 `erp_app.tools` 使用的是 OpenAI function calling 格式（`{type: "function", function: {name: ..., parameters: ...}}`）。这导致 VS Code MCP 扩展无法正确列出工具。

需要将整个项目统一为 MCP 原生格式，涉及：
- `erp_app/tools.py` - 工具定义
- `erp_mcp_service/tools.py` - MCP 工具服务
- `app/clients/mcp_client.py` - MCP 客户端

## What Changes

### erp_app/tools.py
- 将 `TOOL_SCHEMAS` 从 OpenAI 格式改为 MCP 原生格式
- 工具定义直接使用 `{name, description, inputSchema}` 结构
- 移除 `{type: "function", function: {...}}` 嵌套结构

### 新增工具格式转换模块
创建 `erp_app/tools_format.py`，提供 MCP 格式与 OpenAI 格式的双向转换：

```python
# MCP 原生格式 → OpenAI function calling 格式
def to_openai_format(mcp_tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "parameters": mcp_tool.get("inputSchema", {})
        }
    }

# 批量转换供 LLM 调用
def get_openai_tools() -> list:
    return [to_openai_format(t) for t in TOOL_SCHEMAS]
```

### erp_mcp_service/tools.py
- 简化 `list_tools()` 直接使用新的工具格式
- 移除 `_convert_to_mcp_format()` 转换函数（不再需要）
- 保持 `execute_tool()` 和 `call_tool()` 逻辑不变
- **工具名称添加 `mcp_` 前缀**，区分本地服务调用与 MCP 远程调用

| 原名称 | MCP 名称 |
|--------|----------|
| `query_order` | `mcp_query_order` |
| `create_order` | `mcp_create_order` |
| ... | ... |

```python
def list_tools() -> List[Dict[str, Any]]:
    tools = []
    for schema in TOOL_SCHEMAS:
        mcp_name = f"mcp_{schema['name']}"  # 添加前缀
        tools.append({
            "name": mcp_name,
            "description": schema.get("description", ""),
            "inputSchema": schema.get("inputSchema", {}),
            "execution": {"taskSupport": TASK_SUPPORT_MAP.get(schema["name"], "forbidden")}
        })
    return tools
```

### app/llm.py
- LLM 调用时使用 `get_openai_tools()` 获取 OpenAI 格式的工具

### app/clients/mcp_client.py
- 工具解析逻辑从 `result.result.tools` 中提取 `name` 和 `inputSchema`
- 工具调用时将参数封装为 MCP 原生格式

### app/clients/client_factory.py
- 添加 `_mcp_tool_alias` 字典存储工具名称别名映射
- 在 `register_client()` 时注册 MCP 工具别名
- 在 `execute_tool()` 和 `get_risk_level()` 中使用别名查找

```python
class ClientFactory:
    def __init__(self):
        self._mcp_tool_alias = {}  # query_order → mcp_query_order

    def register_client(self, name: str, client):
        for tool in client.get_tools():
            if tool_name.startswith("mcp_"):
                original_name = tool_name[4:]
                self._mcp_tool_alias[original_name] = tool_name

    def execute_tool(self, tool_name: str, args: dict) -> dict:
        # 支持 LLM 返回的名称（无前缀）和 MCP 服务名称（有前缀）
        mcp_name = self._mcp_tool_alias.get(tool_name)
        if mcp_name:
            tool_name = mcp_name
        # ... 执行逻辑
```

### 影响范围
- 所有使用 `TOOL_SCHEMAS` 的模块需要同步更新
- 本地 `erp_adapter` 使用相同的工具格式，需保持一致

## Capabilities

### New Capabilities
- `mcp-native-tools`: 使用 MCP 原生工具格式的能力

### Modified Capabilities
- 移除 `openai-function-tools` 相关能力描述

## Impact

- 统一使用 MCP 原生格式，便于 VS Code MCP 扩展集成
- 消除格式转换层，简化代码逻辑
- 可能影响其他 MCP 客户端的兼容性（如果它们期望 OpenAI 格式）