## Why

当前 MCP Client 和 MCP Service 缺少详细的调用日志，导致调试困难、问题定位耗时。在修复 issue-012 至 issue-015 的过程中，由于缺乏日志可见性，问题排查依赖猜测和试错。需要完整的请求/响应日志来支持深度调试和性能分析。

## What Changes

1. **MCP Client 日志增强**
   - 在 `_request()` 方法中记录每次 HTTP 请求的 method、URL、请求体、执行时间
   - 在 `list_tools()` 和 `call_tool()` 方法中记录调用结果（tools 数量 或 result/error）
   - 在 `_initialize()` 中记录完整握手流程

2. **MCP Service 日志增强**
   - 在 `/mcp`、`/`、`/mcp/tools/list`、`/mcp/tools/call` 端点记录每次请求的 method、请求体、执行时间、响应状态码
   - 在 `_dispatch_method()` 中记录方法分发和执行结果

3. **日志格式统一**
   - 每条日志包含：timestamp、method、params（或简化的 result/error 摘要）、duration（ms）
   - 使用结构化日志格式，便于日志聚合和分析

## Capabilities

### New Capabilities

- `mcp-logging`: MCP 客户端和服务端的完整调用日志记录，包含 method、params、result/error、duration

## Impact

- **代码变更**: `app/clients/mcp_client.py`（添加 `_request`/`list_tools`/`call_tool` 日志）、`erp_mcp_service/main.py`（添加端点和 dispatcher 日志）
- **日志输出**: 增加详细的 MCP 调用日志，便于调试和问题定位
- **无 API 变更**: 仅增加日志输出，不影响接口行为