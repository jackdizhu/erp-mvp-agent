## 1. MCP Client 日志

- [x] 1.1 在 `app/clients/mcp_client.py` 的 `_request()` 方法中添加请求/响应日志，包含 method、url、params、result/error、duration_ms
- [x] 1.2 在 `list_tools()` 方法中添加结果日志，包含 tools_count 和 duration_ms
- [x] 1.3 在 `call_tool()` 方法中添加结果日志，包含 tool、args、result/error、duration_ms
- [x] 1.4 在 `_initialize()` 方法中增强日志，包含 client 发送的 params 和 server 返回的 result
- [x] 1.5 使用 `logging.INFO` 级别和 JSON 格式输出结构化日志

## 2. MCP Service 日志

- [x] 2.1 在 `erp_mcp_service/main.py` 的 `mcp_unified_endpoint()` 中添加请求/响应日志，包含 endpoint、method、params、status、duration_ms
- [x] 2.2 在 `tools_list_legacy()` 和 `tools_call_legacy()` 端点中添加日志
- [x] 2.3 在 `_dispatch_method()` 中添加方法分发和执行结果日志
- [x] 2.4 在响应中记录 status code（200、202、400、500 等）
- [x] 2.5 使用 `logging.INFO` 级别和 JSON 格式输出结构化日志

## 3. 日志格式规范

- [x] 3.1 每条日志包含：timestamp（ISO格式）、level、logger、method、params/args、result/error、duration_ms
- [x] 3.2 使用 Python `logging` 模块的 JSON 格式化输出
- [x] 3.3 logger 名称：`"mcp_client"` 和 `"mcp_service"`

## 4. 验证

- [x] 4.1 启动 MCP Service，发送 initialize 请求，验证日志输出包含完整信息
- [x] 4.2 发送 tools/list 请求，验证日志包含 tools_count
- [x] 4.3 发送 tools/call 请求，验证日志包含 tool、args、result
- [x] 4.4 模拟错误场景，验证错误日志包含 error 信息

## 5. 验证日志示例

### initialize 日志
```json
{"timestamp": "2026-05-31T07:14:00.745653+00:00", "level": "INFO", "logger": "mcp_service", "endpoint": "dispatch", "method": "initialize", "status": 200, "duration_ms": 0.01, "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "result": {"protocolVersion": "2025-03-26"}}
```

### tools/list 日志
```json
{"timestamp": "2026-05-31T07:14:35.594297+00:00", "level": "INFO", "logger": "mcp_service", "endpoint": "dispatch", "method": "tools/list", "status": 200, "duration_ms": 0.01, "result": {"tools_count": 9}}
```

### tools/call 日志
```json
{"timestamp": "2026-05-31T07:15:15.639880+00:00", "level": "INFO", "logger": "mcp_service", "endpoint": "dispatch", "method": "tools/call", "status": 200, "duration_ms": 0.52, "params": {"name": "query_order", "arguments": {"order_id": "123"}}, "result": {"tool": "query_order"}}
```