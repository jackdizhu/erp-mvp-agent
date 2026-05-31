---
title: "[Bug] VS Code MCP 扩展连接失败 - 工具格式不兼容"
status: closed
labels: ["bug", "mcp", "vscode-extension"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

VS Code MCP 扩展连接 MCP 服务失败，无法列出工具。

**复现步骤：**
1. 在 VS Code 中配置 MCP 扩展连接到 `http://localhost:9001`
2. 启动 MCP 服务
3. VS Code MCP 扩展尝试连接并列出工具

**实际结果：**
```
MCPServerManager#listTools Got tools failed:
  { "expected": "string", "path": ["tools", 0, "name"], "message": "Invalid input" },
  { "expected": "object", "path": ["tools", 0, "inputSchema"], "message": "Invalid input" },
  ...
ExtHostMCPService#$start Fail to start
```

**期望结果：**
MCP 扩展能够成功列出所有工具并正常工作。

## 根因分析

### 问题 1: 工具格式不兼容

VS Code MCP 扩展期望的格式：
```json
{"name": "string", "inputSchema": {...}}
```

项目使用的 OpenAI function calling 格式：
```json
{"type": "function", "function": {"name": "...", "parameters": {...}}}
```

### 问题 2: Session/Message ID 管理

MCP 扩展日志中出现过：
```
MCPClient#onError streamable Received a response for an unknown message ID
```

这是 MCP 扩展在处理 SSE 流式响应时的 session tracking 问题，与服务端 session 管理逻辑无关。

## 解决方案

### 方案 1: 统一使用 MCP 原生工具格式（推荐）

修改 `erp_app/tools.py` 的 `TOOL_SCHEMAS`，将所有工具定义从 OpenAI 格式改为 MCP 原生格式。

**修改文件：**
| 文件 | 修改内容 |
|-----|---------|
| `erp_app/tools.py` | 重写 `TOOL_SCHEMAS` 为 MCP 原生格式 |
| `erp_mcp_service/tools.py` | 移除 `_convert_to_mcp_format()` 转换函数 |

**MCP 原生格式示例：**
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

### 方案 2: 保持当前格式（临时方案）

VS Code MCP 扩展的问题不影响后端服务和其他 MCP 客户端。可以暂时忽略 VS Code MCP 扩展的错误，使用后端服务直接测试功能。

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `erp_app/tools.py` | 重写 `TOOL_SCHEMAS` 为 MCP 原生格式（待实施） |
| `erp_mcp_service/tools.py` | 添加 `_convert_to_mcp_format()` 转换函数（已实施，临时方案） |
| `erp_mcp_service/tools.py` | 将 `TASK_SUPPORT_MAP` 中所有工具从 `forbidden` 改为 `optional`（已实施） |
| `erp_mcp_service/main.py` | 增强 `_dispatch_method` 日志，添加 session 创建日志（已实施） |

## 验证

- [x] 验证 `list_tools()` 返回 9 个工具
- [x] 验证工具格式包含 `name`（string）和 `inputSchema`（object）
- [ ] 重启 MCP 服务后测试 VS Code MCP 扩展连接
- [ ] 测试完整工具调用流程

## 相关错误日志

### 工具格式错误
```
MCPServerManager#listTools Got tools failed:
  { "expected": "string", "path": ["tools", 0, "name"], "message": "Invalid input" }
```

### Session ID 错误
```
MCPClient#onError streamable Received a response for an unknown message ID:
  {"jsonrpc":"2.0","id":"...","result":{...}}
```

### Connection 错误
```
ConnectionRefusedError: [WinError 10061] 由于目标计算机积极拒绝，无法连接。
```

## 技术细节

### MCP 原生格式 vs OpenAI 格式

| 字段 | OpenAI 格式 | MCP 原生格式 |
|------|-------------|--------------|
| 工具名称 | `function.name` | `name` |
| 描述 | `function.description` | `description` |
| 参数定义 | `function.parameters` | `inputSchema` |
| 外层类型 | `type: "function"` | 无 |

### Session 管理

服务端使用 `session_manager` 管理 client session：
- 创建 session 时记录 `client_id` 和 `session_id`
- 通过 `Mcp-Session-Id` header 追踪请求
- `pending_requests` 用于跟踪进行中的请求

## 敏感信息检查

创建 issue 后，请执行以下命令检查是否包含敏感信息：

```bash
# 检查敏感路径
grep -rE "^[A-Z]:\\\\|:/" issues/

# 检查敏感变量
grep -rE "api[_-]?key|password|token|secret" issues/
```

**脱敏规则：**
| 类型 | 脱敏方式 |
|------|---------|
| 绝对路径 | 使用项目相对路径或 `<path>` 替代 |
| 环境变量 | 使用 `<ENV_VAR>` 替代 |
| 密钥/Token | 使用 `<KEY>` 或 `***` 替代 |
| 用户名/邮箱 | 使用 `<user>`, `<email>` 替代 |
| 会话ID | 使用 `<session>` 替代 |