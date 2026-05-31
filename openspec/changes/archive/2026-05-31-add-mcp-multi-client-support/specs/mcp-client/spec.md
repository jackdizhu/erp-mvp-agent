## MODIFIED Requirements

### Requirement: MCP Client Request ID Format
MCP 客户端 SHALL 使用 UUID v4 格式生成每个 JSON-RPC 请求的 `id` 字段。客户端 SHALL 在 `__init__` 时生成唯一 `client_id`（UUID v4），并在所有 HTTP 请求中通过 `X-Client-Id` header 携带。

#### Scenario: Client generates UUID request IDs
- **WHEN** MCPClient 实例创建并发送请求
- **THEN** 每个请求的 `id` 字段为独立的 UUID v4 字符串

#### Scenario: Client sends X-Client-Id header
- **WHEN** MCPClient 发送任何 HTTP 请求
- **THEN** 请求头包含 `X-Client-Id`，值为客户端初始化时生成的 UUID