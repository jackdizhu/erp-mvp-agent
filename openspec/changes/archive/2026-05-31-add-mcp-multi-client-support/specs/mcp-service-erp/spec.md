## MODIFIED Requirements

### Requirement: MCP Service Request Tracking
MCP 服务端 SHALL 从请求头提取 `X-Client-Id` 标识客户端来源，并在 Session 中维护 `pending_requests` 字典追踪未完成请求。响应 SHALL 严格回显请求 `id`。

#### Scenario: Server extracts client ID from header
- **WHEN** 服务端收到携带 `X-Client-Id` header 的请求
- **THEN** 将 client_id 关联到当前 session

#### Scenario: Server tracks pending requests per session
- **WHEN** 服务端收到 JSON-RPC 请求并开始处理
- **THEN** 将 request_id 记录到 session 的 pending_requests 中

#### Scenario: Server removes completed request from tracking
- **WHEN** 服务端返回 JSON-RPC 响应
- **THEN** 从 pending_requests 中移除对应 request_id