## 1. Session Manager

- [x] 1.1 Create `erp_mcp_service/session_manager.py` with `Session` dataclass
- [x] 1.2 Implement session creation with UUID generation
- [x] 1.3 Implement session validation
- [x] 1.4 Implement session termination (close SSE connections)
- [x] 1.5 Implement message queue for SSE push
- [x] 1.6 Implement session TTL and cleanup

## 2. POST /mcp SSE Response

- [x] 2.1 Add SSE response format helper function `_build_sse_content()`
- [x] 2.2 Modify `mcp_unified_endpoint` to detect Accept header and choose response format
- [x] 2.3 Add `Mcp-Session-Id` header to initialize response
- [x] 2.4 Validate `Mcp-Session-Id` on non-initialize requests
- [x] 2.5 Add `MCP-Protocol-Version` header to all responses
- [x] 2.6 Fix `_validate_accept_header` to accept `application/json` OR `text/event-stream`

## 3. GET /mcp SSE Endpoint

- [x] 3.1 Add `GET /mcp` endpoint with SSE streaming
- [x] 3.2 Implement keep-alive ping (30s interval)
- [x] 3.3 Implement message push from session queue
- [x] 3.4 Handle connection close and cleanup

## 4. DELETE /mcp Session Termination

- [x] 4.1 Add `DELETE /mcp` endpoint
- [x] 4.2 Validate `Mcp-Session-Id` header
- [x] 4.3 Close all associated SSE connections
- [x] 4.4 Remove session from storage

## 5. Testing

- [x] 5.1 Test IDE connection with SSE response format
- [x] 5.2 Test `GET /mcp` SSE stream with keep-alive
- [x] 5.3 Test session creation on initialize
- [x] 5.4 Test session validation on subsequent requests
- [x] 5.5 Test `DELETE /mcp` session termination
- [x] 5.6 Test JSON-only client still works