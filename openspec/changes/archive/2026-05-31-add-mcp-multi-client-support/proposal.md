## Why

MCP 服务在多客户端同时连接时，JSON-RPC 请求 ID 格式不统一导致 `unknown message ID` 错误。ERP Agent 客户端使用 Python 对象地址生成 ID（如 `init_140123456789`），而 Trae IDE 等外部客户端使用 UUID 格式，服务端无法正确匹配请求与响应，造成连接失败。

## What Changes

- 客户端统一使用 UUID v4 生成 JSON-RPC 请求 ID，替换当前 `f"init_{id(self)}"` 和 `f"req_{id(self)}"` 格式
- 服务端增加 `X-Client-Id` 请求头支持，按客户端标识隔离请求追踪
- 服务端在 session 中维护 `pending_requests` 映射（request_id → 状态），确保多客户端并发请求不冲突
- 服务端响应中严格回显客户端发送的 request id，符合 JSON-RPC 2.0 规范

## Capabilities

### New Capabilities
- `mcp-multi-client`: 多客户端并发连接支持，包含 UUID 请求 ID 生成、X-Client-Id 客户端标识、服务端请求追踪隔离

### Modified Capabilities
- `mcp-client`: 请求 ID 生成方式从对象地址改为 UUID v4
- `mcp-service-erp`: 增加 X-Client-Id header 解析和 pending_requests 追踪

## Impact

- `app/clients/mcp_client.py` - 修改请求 ID 生成逻辑，添加 X-Client-Id header
- `erp_mcp_service/main.py` - 添加 X-Client-Id 解析，pending_requests 追踪
- `erp_mcp_service/session_manager.py` - Session 增加 pending_requests 字段
- MCP 协议兼容性：纯增强，无 **BREAKING** 变更，旧客户端仍可正常连接