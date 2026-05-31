## Why

MCP Service 当前 POST /mcp 端点只返回 `application/json` 格式响应，不符合 MCP 2025-11-25 Streamable HTTP 传输规范。IDE (TRAE) 期望 SSE 格式响应，导致连接失败（"Received a response for an unknown message ID"）。同时缺少 GET /mcp SSE 端点（405 错误）和会话管理。

## What Changes

1. **POST /mcp SSE 响应支持**
   - 当客户端 Accept 包含 `text/event-stream` 时，用 SSE 格式包装 JSON-RPC 响应
   - 当客户端只接受 `application/json` 时，保持现有 JSON 响应

2. **GET /mcp SSE 端点**
   - 支持 SSE 长连接，用于服务端主动推送通知
   - 支持 keep-alive ping 防止连接超时

3. **Session 管理**
   - 初始化时生成 `Mcp-Session-Id`
   - 后续请求验证 Session ID
   - 支持 DELETE /mcp 终止会话

## Capabilities

### New Capabilities
- `mcp-streamable-http`: 完整 Streamable HTTP 传输支持（POST SSE + GET SSE + Session）

### Modified Capabilities
- 无

## Impact

- **修改文件**:
  - `erp_mcp_service/main.py` - 端点改造，SSE 响应，会话管理
- **新增文件**:
  - `erp_mcp_service/session_manager.py` - 会话状态管理
- **测试影响**:
  - IDE 连接测试
  - SSE 格式验证
  - 会话生命周期测试