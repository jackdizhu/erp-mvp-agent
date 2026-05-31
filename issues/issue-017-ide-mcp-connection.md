---
title: "[Bug] IDE MCP 无法连接 - 协议版本不匹配 + SSE 响应格式错误"
status: closed
labels: ["bug", "mcp", "transport"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

IDE (TRAE) 配置 MCP 服务 `erp`，连接失败。

**复现步骤：**
1. 在 IDE MCP 配置中添加 `erp` 服务，URL: `http://localhost:9001`
2. 配置 `X-API-Key` header
3. 尝试连接 MCP 服务

**实际结果：**
```
MCPClient#onError streamable Unsupported protocol version
MCPClient#startFailed sse SSE error: Non-200 status code (405)
ExtHostMCPService#$start Fail to start
```

**期望结果：**
IDE 成功连接 MCP 服务，可调用 tools/list 等方法。

---

## 根因分析

### 问题 1: 协议版本不匹配
- 服务端 `PROTOCOL_VERSION = "2025-03-26"`
- IDE 请求 `protocolVersion: "2025-11-25"`
- 服务端严格检查版本，拒绝连接

### 问题 2: SSE 响应格式错误
- 服务端 POST /mcp 只返回 `Content-Type: application/json`
- IDE 的 Streamable HTTP 客户端期望 `Content-Type: text/event-stream` (SSE 格式)
- 客户端无法解析响应，导致 "unknown message ID" 错误

### 问题 3: 缺少 GET /mcp 端点
- 服务端没有注册 `GET /mcp` 端点
- IDE SSE 模式 fallback 请求返回 405 Method Not Allowed

### 问题 4: 缺少会话管理
- 服务端没有 `Mcp-Session-Id` header 支持
- 无法跟踪会话状态

---

## 解决方案

### 变更 1: 协议版本升级
```python
# erp_mcp_service/main.py
PROTOCOL_VERSION = "2025-11-25"

# app/clients/mcp_client.py
PROTOCOL_VERSION = "2025-11-25"
```

### 变更 2: MCP Tasks 功能
- 新增 `task_manager.py` - 任务状态管理
- 实现 `tasks/start`, `tasks/status`, `tasks/complete`, `tasks/cancel`, `tasks/list` 方法
- 工具支持 `execution.taskSupport` 声明

### 变更 3: Streamable HTTP 传输
- POST /mcp 支持 SSE StreamingResponse
- 新增 GET /mcp SSE 长连接端点
- 新增 DELETE /mcp 会话终止
- 新增 session_manager.py 会话管理

### 变更 4: 响应模式配置
- 服务端 `.env` 新增 `MCP_RESPONSE_MODE` 参数
- 客户端 header `X-MCP-Response-Mode` 覆盖服务端配置
- 支持 `sse` / `json` / `auto` 三种模式

---

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `erp_mcp_service/main.py` | 协议版本升级 + SSE 响应 + GET/DELETE 端点 + 会话管理 |
| `erp_mcp_service/task_manager.py` | 新增 - 任务状态管理器 |
| `erp_mcp_service/session_manager.py` | 新增 - 会话状态管理器 |
| `erp_mcp_service/tools.py` | 新增 TASK_SUPPORT_MAP + taskSupport 声明 |
| `erp_mcp_service/config.py` | 新增 MCP_RESPONSE_MODE 配置 |
| `app/clients/mcp_client.py` | 协议版本升级 |
| `.env` | 新增 MCP_RESPONSE_MODE=sse |
| `openspec/changes/mcp-protocol-version-and-tasks-support/` | 新增 - 变更提案 |
| `openspec/changes/mcp-streamable-http-transport/` | 新增 - 变更提案 |

---

## 验证

- [x] curl 测试 `POST /mcp` 返回 SSE 格式响应
- [x] curl 测试 `GET /mcp` SSE 流 + keep-alive ping
- [x] curl 测试 Session 创建 (`Mcp-Session-Id` header)
- [x] curl 测试 `X-MCP-Response-Mode: json` 返回 JSON 格式
- [x] curl 测试 `X-MCP-Response-Mode: sse` 返回 SSE 格式
- [x] curl 测试 `DELETE /mcp` 终止会话
- [ ] **IDE 连接验证** - 待用户测试

---

## 敏感信息检查

无敏感信息泄露。

---

## IDE MCP 配置示例

```json
{
  "mcpServers": {
    "erp": {
      "url": "http://localhost:9001",
      "headers": {
        "X-API-Key": "***",
        "X-MCP-Response-Mode": "sse"
      }
    }
  }
}
```