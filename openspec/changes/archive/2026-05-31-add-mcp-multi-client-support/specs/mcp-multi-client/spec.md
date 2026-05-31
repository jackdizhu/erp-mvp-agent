## ADDED Requirements

### Requirement: UUID v4 Request ID Generation
MCP 客户端 SHALL 为每个 JSON-RPC 请求生成 UUID v4 格式的 `id` 字段，替换当前基于 Python 对象地址的 ID 生成方式。

#### Scenario: Initialize request uses UUID
- **WHEN** 客户端发送 `initialize` 请求
- **THEN** 请求体中 `id` 字段为 UUID v4 格式字符串（如 `"550e8400-e29b-41d4-a716-446655440000"`）

#### Scenario: Tools list request uses UUID
- **WHEN** 客户端发送 `tools/list` 请求
- **THEN** 请求体中 `id` 字段为 UUID v4 格式字符串

#### Scenario: Tools call request uses UUID
- **WHEN** 客户端发送 `tools/call` 请求
- **THEN** 请求体中 `id` 字段为 UUID v4 格式字符串

### Requirement: X-Client-Id Header
MCP 客户端 SHALL 在每个 HTTP 请求中携带 `X-Client-Id` header，值为客户端实例的唯一标识（UUID v4）。客户端在初始化时生成一次，后续请求复用。

#### Scenario: First request includes X-Client-Id
- **WHEN** 客户端发送首次请求（initialize）
- **THEN** 请求头包含 `X-Client-Id`，值为 UUID v4 格式

#### Scenario: Subsequent requests reuse X-Client-Id
- **WHEN** 客户端发送后续请求
- **THEN** 请求头中 `X-Client-Id` 与首次请求相同

### Requirement: Server Client Identification
MCP 服务端 SHALL 从请求头中提取 `X-Client-Id`，若不存在则分配默认值 `"anonymous"`。服务端 SHALL 将 client_id 关联到 session。

#### Scenario: Request with X-Client-Id
- **WHEN** 服务端收到携带 `X-Client-Id: abc-123` 的请求
- **THEN** 服务端记录该请求来自客户端 `abc-123`

#### Scenario: Request without X-Client-Id
- **WHEN** 服务端收到未携带 `X-Client-Id` 的请求
- **THEN** 服务端将该请求标记为来自客户端 `"anonymous"`

### Requirement: Pending Requests Tracking
MCP 服务端 SHALL 在 Session 中维护 `pending_requests` 字典（request_id → timestamp），记录未完成的请求。请求完成或超过 60 秒后自动移除。

#### Scenario: Request tracked on receive
- **WHEN** 服务端收到 JSON-RPC 请求
- **THEN** 将 request_id 和当前时间戳写入 session 的 pending_requests

#### Scenario: Request removed on response
- **WHEN** 服务端返回 JSON-RPC 响应
- **THEN** 从 session 的 pending_requests 中移除该 request_id

#### Scenario: Expired requests cleaned up
- **WHEN** pending_requests 中的请求超过 60 秒未完成
- **THEN** 在 session cleanup 时自动移除该记录

### Requirement: Strict Request ID Echo
MCP 服务端 SHALL 在 JSON-RPC 响应中严格回显客户端发送的 `id` 字段值，符合 JSON-RPC 2.0 规范。

#### Scenario: Response echoes request ID
- **WHEN** 服务端处理 `id` 为 `"550e8400-e29b-41d4-a716-446655440000"` 的请求
- **THEN** 响应体中 `id` 字段为 `"550e8400-e29b-41d4-a716-446655440000"`

#### Scenario: Notification has null ID
- **WHEN** 服务端处理无 `id` 的通知（如 `notifications/initialized`）
- **THEN** 响应体中 `id` 为 `null`