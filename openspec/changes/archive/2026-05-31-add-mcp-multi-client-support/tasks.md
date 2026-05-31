## 1. Client UUID Request ID

- [x] 1.1 修改 `app/clients/mcp_client.py`：`__init__` 中生成 `self._client_id = str(uuid.uuid4())`
- [x] 1.2 修改 `app/clients/mcp_client.py`：`_initialize` 方法中 `request_id` 改为 `str(uuid.uuid4())`
- [x] 1.3 修改 `app/clients/mcp_client.py`：`list_tools` 方法中 `request_id` 改为 `str(uuid.uuid4())`
- [x] 1.4 修改 `app/clients/mcp_client.py`：`call_tool` 方法中 `request_id` 改为 `str(uuid.uuid4())`
- [x] 1.5 修改 `app/clients/mcp_client.py`：`_request` 方法中 headers 添加 `X-Client-Id: self._client_id`

## 2. Server Client Identification

- [x] 2.1 修改 `erp_mcp_service/main.py`：`mcp_unified_endpoint` 中提取 `X-Client-Id` header，默认值 `"anonymous"`
- [x] 2.2 修改 `erp_mcp_service/main.py`：`initialize` 响应中将 `client_id` 关联到 session
- [x] 2.3 修改 `erp_mcp_service/main.py`：日志中增加 `client_id` 字段

## 3. Session Pending Requests Tracking

- [x] 3.1 修改 `erp_mcp_service/session_manager.py`：Session 数据类增加 `pending_requests: Dict[str, float]` 字段
- [x] 3.2 修改 `erp_mcp_service/session_manager.py`：增加 `track_request(request_id)` 方法
- [x] 3.3 修改 `erp_mcp_service/session_manager.py`：增加 `complete_request(request_id)` 方法
- [x] 3.4 修改 `erp_mcp_service/session_manager.py`：`cleanup_expired` 中清理超过 60 秒的 pending_requests

## 4. Server Request ID Echo

- [x] 4.1 修改 `erp_mcp_service/main.py`：`_dispatch_method` 入口处调用 `session.track_request(request_id)`
- [x] 4.2 修改 `erp_mcp_service/main.py`：`_dispatch_method` 返回前调用 `session.complete_request(request_id)`
- [x] 4.3 修改 `erp_mcp_service/main.py`：验证所有响应路径中 `id` 字段严格等于请求 `id`

## 5. Verification

- [x] 5.1 启动 MCP 服务，验证单客户端连接正常
- [x] 5.2 使用 curl 模拟多客户端并发请求，验证 ID 隔离
- [x] 5.3 验证 Trae IDE MCP 客户端连接不再报 `unknown message ID`