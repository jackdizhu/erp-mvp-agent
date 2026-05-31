## ADDED Requirements

### Requirement: POST /mcp SSE response format
The server SHALL return SSE format response when client Accept header includes `text/event-stream`.

#### Scenario: Client accepts SSE
- **WHEN** client sends `POST /mcp` with `Accept: application/json, text/event-stream`
- **THEN** server returns `Content-Type: text/event-stream`
- **AND** body is SSE format:
  ```
  event: message\r\n
  data: {"jsonrpc":"2.0","id":"xxx","result":{...}}\r\n
  \r\n
  ```

#### Scenario: Client accepts only JSON
- **WHEN** client sends `POST /mcp` with `Accept: application/json`
- **THEN** server returns `Content-Type: application/json`
- **AND** body is plain JSON-RPC response

### Requirement: GET /mcp SSE endpoint
The server SHALL support `GET /mcp` for server-initiated SSE streams.

#### Scenario: Open SSE stream
- **WHEN** client sends `GET /mcp` with `Accept: text/event-stream`
- **THEN** server returns `Content-Type: text/event-stream`
- **AND** keeps connection open for server-push messages
- **AND** sends keep-alive ping every 30 seconds

#### Scenario: No Accept header for SSE
- **WHEN** client sends `GET /mcp` without `Accept: text/event-stream`
- **THEN** server returns `405 Method Not Allowed`

### Requirement: Session management via Mcp-Session-Id
The server SHALL generate and validate `Mcp-Session-Id` for session tracking.

#### Scenario: Initialize creates session
- **WHEN** server processes `initialize` request
- **THEN** server generates UUID session ID
- **AND** returns it in `Mcp-Session-Id` response header

#### Scenario: Subsequent requests include session
- **WHEN** client sends request with `Mcp-Session-Id` header
- **THEN** server validates session exists
- **AND** returns `400 Bad Request` if session not found

#### Scenario: Request without session after initialization
- **WHEN** client sends non-initialize request without `Mcp-Session-Id`
- **AND** server has active sessions
- **THEN** server returns `400 Bad Request`

### Requirement: DELETE /mcp session termination
The server SHALL support `DELETE /mcp` for explicit session termination.

#### Scenario: Terminate session
- **WHEN** client sends `DELETE /mcp` with valid `Mcp-Session-Id`
- **THEN** server removes session
- **AND** closes all associated SSE connections
- **AND** returns `200 OK`

#### Scenario: Delete without session
- **WHEN** client sends `DELETE /mcp` without `Mcp-Session-Id`
- **THEN** server returns `405 Method Not Allowed`

### Requirement: Server-push notifications via SSE
The server SHALL support pushing JSON-RPC notifications to connected SSE clients.

#### Scenario: Push notification
- **WHEN** server has a notification to send
- **AND** client has active SSE connection (GET /mcp)
- **THEN** server sends notification via SSE stream:
  ```
  event: message\r\n
  data: {"jsonrpc":"2.0","method":"notifications/...","params":{...}}\r\n
  \r\n
  ```

### Requirement: MCP-Protocol-Version header
The server SHALL include `MCP-Protocol-Version` header in all responses.

#### Scenario: Response includes protocol version
- **WHEN** server sends any response
- **THEN** response includes `MCP-Protocol-Version: 2025-11-25` header