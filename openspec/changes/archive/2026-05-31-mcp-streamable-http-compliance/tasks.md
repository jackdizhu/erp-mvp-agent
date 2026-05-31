## 1. MCP Service 端点重构

- [x] 1.1 在 `erp_mcp_service/main.py` 中新增 `_dispatch_method()` 函数，按 JSON-RPC `method` 字段分发请求（initialize / notifications/initialized / tools/list / tools/call）
- [x] 1.2 新增 `POST /mcp` 端点，调用 `_dispatch_method()`，添加 `MCP-Protocol-Version: 2025-03-26` 响应头
- [x] 1.3 新增 `POST /` 端点，复用 `_dispatch_method()`，兼容 IDE 默认配置
- [x] 1.4 实现 `initialize` 方法处理：解析 client `protocolVersion`、`capabilities`、`clientInfo`，返回服务端 `protocolVersion`、`capabilities`（tools/resources/prompts/logging）、`serverInfo`、`instructions`
- [x] 1.5 实现版本协商逻辑：若 client 请求的版本不是 `2025-03-26`，返回 error `-32602`
- [x] 1.6 实现 `notifications/initialized` 处理：返回 HTTP 202 Accepted 无 body
- [x] 1.7 实现 `tools/list` 方法分发：调用 `list_tools()` 返回 JSON-RPC result
- [x] 1.8 实现 `tools/call` 方法分发：调用 `call_tool()` 返回 JSON-RPC result
- [x] 1.9 实现 `Accept` 头校验：缺少 `application/json` 或 `text/event-stream` 时返回 400
- [x] 1.10 实现未知 method 错误响应：返回 JSON-RPC error code -32601
- [x] 1.11 改造旧路由 `/mcp/tools/list` 和 `/mcp/tools/call`，内部调用 `_dispatch_method()` 复用逻辑

## 2. MCP Client 握手适配

- [x] 2.1 修改 `app/clients/mcp_client.py` 的 `_request()` 方法：请求路径从 `/mcp/tools/list` 改为 `/mcp`
- [x] 2.2 新增 `_initialize()` 方法：构建 initialize JSON-RPC 请求，包含 `protocolVersion: "2025-03-26"`、`capabilities`、`clientInfo`，发送到 `/mcp`
- [x] 2.3 新增 `_send_initialized_notification()` 方法：构建 `notifications/initialized` JSON-RPC 通知（无 id），发送到 `/mcp`
- [x] 2.4 修改 `list_tools()` 方法：首次调用前检查 `_initialized` 标志，若未初始化则调用 `_initialize()` + `_send_initialized_notification()`
- [x] 2.5 修改 `call_tool()` 方法：同样检查并执行懒初始化
- [x] 2.6 添加 `_initialized` 和 `_server_info` 实例变量，缓存初始化状态
- [x] 2.7 处理 initialize 错误响应（如版本不支持），抛出合适的异常
- [x] 2.8 修改 `list_tools()` 方法：使用 `method: "tools/list"` 发送到 `/mcp` 端点
- [x] 2.9 修改 `call_tool()` 方法：使用 `method: "tools/call"` 发送到 `/mcp` 端点

## 3. MCP 端口与 URL 配置

- [x] 3.1 确认 `erp_mcp_service/config.py` 默认端口已改为 9001（已完成）
- [x] 3.2 在 `app/config.py` 中新增 `MCP_SERVICE_URL` 环境变量读取
- [x] 3.3 修改 `app/clients/mcp_registry.py` 的 `_register_services()`：优先使用 `MCP_SERVICE_URL` 环境变量覆盖 JSON 配置中的 URL
- [x] 3.4 在 `_register_services()` 中添加 INFO 日志，输出实际使用的 URL 来源（env 或 config）
- [x] 3.5 更新 `app/config_dir/mcp_servers.json` 默认 URL 为 `http://localhost:9001/mcp`

## 4. 验证与测试

- [x] 4.1 启动 MCP Service，验证 `curl -X POST http://localhost:9001/mcp` 返回正确响应
- [x] 4.2 验证 `curl -X POST http://localhost:9001/` 返回正确响应（根路径兼容）
- [x] 4.3 验证 `initialize` 握手流程：
  - 发送 initialize → 收到 `protocolVersion`、`capabilities`、`serverInfo`
  - 发送 notifications/initialized → 收到 HTTP 202
- [x] 4.4 验证 initialize 版本协商：
  - 发送 `protocolVersion: "2025-03-26"` → 收到相同版本
  - 发送 `protocolVersion: "1.0.0"` → 收到错误 `{"code": -32602, "message": "Unsupported protocol version", "data": {"supported": ["2025-03-26"], "requested": "1.0.0"}}`
- [x] 4.5 验证 `tools/list` via unified endpoint（返回 9 个工具）
- [x] 4.6 验证旧路由 `/mcp/tools/list` 仍可正常工作
- [x] 4.7 验证 `MCP_SERVICE_URL` 环境变量覆盖 JSON 配置（在代码中已实现）
- [x] 4.8 验证 `Accept` 头缺失时返回 400
- [x] 4.9 验证 `MCP-Protocol-Version` 响应头存在（通过检查响应 headers）
- [ ] 4.10 在 Trae IDE 中配置 MCP 服务 URL，验证 IDE 可正常发现和连接

## 5. 握手流程时序图（参考）

```
Client                              Server
  │                                    │
  │── POST /mcp ──────────────────────▶│
  │   method: "initialize"              │
  │   protocolVersion: "2025-03-26"   │
  │   capabilities: {...}               │
  │   clientInfo: {...}                │
  │                                    │
  │◀── 200 OK ─────────────────────────│
  │   protocolVersion: "2025-03-26"   │
  │   capabilities: {...}              │
  │   serverInfo: {...}               │
  │   instructions: "..."             │
  │                                    │
  │── POST /mcp ──────────────────────▶│
  │   method: "notifications/          │
  │   initialized"                    │
  │                                    │
  │◀── 202 Accepted ──────────────────│
  │                                    │
  │── POST /mcp ──────────────────────▶│  ← 现在可以调用工具了
  │   method: "tools/list"             │
  │                                    │
  │◀── 200 OK ─────────────────────────│
  │   result: {tools: [...]}          │
```