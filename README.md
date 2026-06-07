# ERP MVP Agent

An ERP Agent system powered by LLM Tool Calling. Validate whether AI can stably drive ERP operation closed loops.

[中文版](README.zh.md)

## Overview

**Core Capability:** Natural language-driven ERP operations with MCP protocol multi-client routing, two-phase risk approval, and streaming responses.

```
User (Natural Language)
   ↓
Agent (Intent Recognition + Tool Selection + Force Retry)
   ↓
ClientFactory (MCP / Local Adapter / Hybrid Routing)
   ↓
ERP Service (SQLite Persistence + Service Layer)
```

## Core Advantages

| Advantage | Description |
|-----------|-------------|
| **Native MCP Protocol** | Implements MCP Streamable HTTP spec (2025-11-25) with JSON-RPC 2.0, session management, async Tasks |
| **Multi-Backend Smart Routing** | ClientFactory dispatches to MCP remote services, local ERP adapter; supports mcp/hybrid/local mode hot-switching |
| **Two-Phase Approval Loop** | Frontend validation (ApprovalStore) → User decision (user_op_id) → Agent execution, prevents approval bypass |
| **Intent Fallback** | When LLM skips tool calls, intent detection engine auto-identifies and forces retry, eliminating hallucination risk |
| **Full-Chain Observability** | SessionLogger records every LLM request/response/tool call/approval result, JSONL persistence + auto cleanup |
| **Externalized Prompts** | System prompts decoupled from code to prompts.yaml, supports runtime changes without restart |

## Features

| Feature | Description |
|---------|-------------|
| **Natural Language ERP** | Query orders, inventory, suppliers through chat |
| **MCP Protocol Integration** | Full MCP Streamable HTTP implementation, SSE/JSON dual-mode response |
| **Tool Calling** | LLM-driven routing system with 9 built-in tools + MCP dynamic extension |
| **Risk-Based Approval** | SAFE/CAUTION/DANGER levels with two-phase confirmation flow |
| **Session Management** | Multi-session support with localStorage persistence |
| **Streaming Response** | SSE real-time push, typewriter effect, tool status visualization |
| **Error Handling** | 4-layer error model (LLM/TOOL/DATA/SYS) + MCP-specific error types |
| **Session Logging** | JSONL persistence, stream-buffered writes, 7-day auto cleanup |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React + Vite (no external UI libraries) |
| **Agent Service** | FastAPI (Python), port 9000 |
| **MCP Service** | FastAPI (Python), port 9001, JSON-RPC 2.0 |
| **AI** | LLM API (OpenAI-compatible) |
| **Data** | SQLite (WAL mode) + Service Layer |
| **Protocol** | MCP Streamable HTTP (2025-11-25) |

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### Configuration

Copy the default environment file and modify:

```bash
cp .default.env .local.env
# Edit .local.env with your API Key and other settings
```

### Backend Setup

```bash
pip install -r app/requirements.txt

# Start Agent service (includes ERP internal service)
python -m app.main

# Start MCP service (optional, required when CLIENT_BACKEND=mcp)
pip install -r erp_mcp_service/requirements.txt
python -m erp_mcp_service.main
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Start Both

Use the provided script:

```bash
./start.sh
```

## Usage Examples

### Query Order
```
User: What's the status of order 123?
Agent: Order 123 is currently shipping, expected delivery on June 1st.
```

### Create Purchase Order
```
User: Create a purchase order for supplier A: iPhone 15 ×10
Agent: Purchase order created: PO-1001
```

### Inventory Check
```
User: Do we have enough iPhone 15 stock for 100 units order?
Agent: Current stock is 60 units, insufficient for 100. Suggest split order or restocking.
```

### Update with Approval
```
User: Change order 123 shipping address to Beijing Chaoyang District
Agent: [Approval Card] Confirm update order 123 address field?
```

## API Reference

### POST /chat

Send a message and receive Agent response.

**Request:**
```json
{
  "message": "Query order 123",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi, how can I help?"}
  ],
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "reply": "Order 123 is shipping",
  "tool_calls": [
    {"tool": "query_order", "args": {"order_id": "123"}, "result": {...}}
  ],
  "pending_action": {
    "status": "PENDING",
    "action_id": "act_xxx",
    "tool": "update_order",
    "risk_level": "DANGER",
    "title": "Update Order",
    "summary": "Update order 123 address",
    "description": "...",
    "warning": null,
    "detail": {...},
    "expires_at": 1717200000,
    "ttl_seconds": 300
  },
  "error": null
}
```

### POST /chat/confirm

Confirm or reject a pending action.

**Request:**
```json
{
  "action_id": "act_xxx",
  "approved": true,
  "history": [...],
  "session_id": "optional-session-id",
  "user_op_id": "uop_xxx"
}
```

### POST /chat/stream

SSE streaming response with real-time Agent execution status.

**Request:** Same format as `/chat`.

**Response:** `text/event-stream` format with the following event types:

| Event | Description | Data Format |
|-------|-------------|-------------|
| `thinking` | Agent thinking phase | `{"stage": "analyzing_intent", "message": "Analyzing your intent..."}` |
| `tool_call` | Tool call started | `{"tool": "query_order", "args": {...}, "status": "executing"}` |
| `tool_result` | Tool execution result | `{"tool": "query_order", "result": {...}, "status": "completed"}` |
| `reply_chunk` | LLM reply fragment | `{"content": "Or"}` |
| `done` | Completion marker | `{"complete": true, "tool_calls": [...], "pending_action": null}` |

### POST /api/approval/create

Frontend creates an approval record after receiving approval info.

**Request:**
```json
{"action_id": "act_xxx"}
```

**Response:**
```json
{
  "supported": true,
  "action_id": "act_xxx",
  "fields": ["address"],
  "irreversible": false,
  "warning": null
}
```

### POST /api/approval/decide

User approves/rejects, generating a user operation ID.

**Request:**
```json
{"action_id": "act_xxx", "approved": true}
```

**Response:**
```json
{
  "user_op_id": "uop_xxx",
  "action_id": "act_xxx",
  "approved": true,
  "status": "approved"
}
```

### POST /api/mcp/reload

Hot-reload MCP service registry.

### GET /api/mcp/debug

View MCP client registration status.

### GET /health

Health check, returns service status and configuration info.

## Architecture

```
/app                          # Agent Service (port 9000)
  main.py                     # API entry point (7 endpoints)
  agent.py                    # Agent core loop (chat/stream_chat/confirm)
  llm.py                      # LLM call wrapper (sync + streaming)
  clients/
    client_factory.py         # Tool routing factory (MCP/local adapter/hybrid)
    mcp_client.py             # MCP client (Streamable HTTP)
    mcp_registry.py           # MCP service registry (hot-reload)
    erp_adapter.py            # Local ERP adapter
    base.py                   # Client base class
  approval_core.py            # Approval core logic (create/confirm/expiry cleanup)
  approval_store.py           # Approval record store (two-phase validation)
  intent_detector.py          # Intent detection engine
  agent_logger.py             # Session logger (JSONL persistence + stream buffer)
  prompt_config.py            # Prompt externalization manager
  config.py                   # Configuration center
  errors.py                   # Unified error model
  models.py                   # Pydantic data models
  erp_client.py               # ERP client wrapper
  config_dir/
    prompts.yaml              # System prompt configuration
    intent_rules.json         # Intent detection rules
    mcp_servers.json          # MCP service registration config

/erp_app                      # ERP Business Service (internal module)
  main.py                     # ERP internal API (/erp/tools/*, /erp/approval/*)
  tools.py                    # Tool registry & execution (9 tools)
  tools_format.py             # Tool schema formatting
  db.py                       # SQLite data layer (WAL mode, thread-safe)
  seed.py                     # Seed data
  models.py                   # Data models
  schemas.py                  # Pydantic schemas
  approval_detail.py          # Approval detail generation
  config.py                   # Business configuration
  errors.py                   # Business errors
  services/
    order_service.py          # Order service (create/update/cancel/delete)
    inventory_service.py      # Inventory service (adjust)
    supplier_service.py       # Supplier service

/erp_mcp_service              # MCP Standalone Service (port 9001)
  main.py                     # MCP Streamable HTTP endpoint
  tools.py                    # MCP tool list & execution
  approval_manager.py         # MCP approval management
  session_manager.py          # MCP session management
  task_manager.py             # Async task management
  config.py                   # MCP service configuration

/frontend/src
  App.jsx                     # Root component
  ChatPage.jsx                # Chat UI & message rendering
  StreamingMessage.jsx        # Streaming message component
  ThinkingIndicator.jsx       # Thinking status indicator
  ToolStatusCard.jsx          # Tool status card
  DataVizCard.jsx             # Data visualization card
  ApprovalCard.jsx            # Risk approval card
  McpErrorNotification.jsx    # MCP error notification component
  useStreamingChat.js         # SSE streaming connection manager
  SessionManager.js           # Session state management
  httpUtils.js                # HTTP utility functions
```

## Tool System

| Tool | Risk Level | Description |
|------|-----------|-------------|
| query_order | SAFE | Query single order |
| query_orders | SAFE | Batch query orders |
| query_inventory | SAFE | Check inventory |
| query_supplier | SAFE | Query supplier info |
| create_order | CAUTION | Create order (limit: 5 items) |
| update_order | DANGER | Update order fields (requires approval) |
| cancel_order | DANGER | Cancel order (requires approval) |
| delete_order | DANGER | Delete order (requires approval, irreversible) |
| adjust_inventory | DANGER | Adjust inventory levels (requires approval) |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| OPENAI_API_KEY | - | LLM API key |
| OPENAI_BASE_URL | https://api.openai.com/v1 | Custom API endpoint |
| LLM_MODEL | gpt-4o | Model selection |
| CLIENT_BACKEND | mcp | Tool routing mode: mcp / hybrid / local |
| ENABLE_LOCAL_ADAPTER | false | Enable local ERP adapter |
| MCP_SERVICE_URL | http://localhost:9001 | MCP service URL |
| MCP_SERVICE_PORT | 9001 | MCP service port |
| MCP_API_KEY | - | MCP service API key |
| MCP_RESPONSE_MODE | sse | MCP response mode: sse / json / auto |
| BACKEND_PORT | 9000 | Agent service port |
| APPROVAL_TTL | 300 | Approval timeout (seconds) |
| APPROVAL_MAX_PENDING | 10 | Max pending approvals |
| HISTORY_WINDOW_N | 6 | Context window size |
| TOOL_LIMIT_CREATE | 5 | Max items per create order |
| TOOL_LIMIT_UPDATE | 5 | Max items per update order |
| TOOL_LIMIT_BATCH | 10 | Max batch query size |
| LLM_TIMEOUT | 15 | LLM call timeout (seconds) |
| MCP_REQUEST_TIMEOUT | 10 | MCP request timeout (seconds) |
| MCP_CONNECT_TIMEOUT | 5 | MCP connect timeout (seconds) |
| SSE_PING_INTERVAL | 15 | SSE heartbeat interval (seconds) |
| SSE_TIMEOUT | 60 | SSE connection timeout (seconds) |
| SSE_MAX_CHUNK | 500 | SSE max chunk size |
| INTENT_RULES_PATH | app/config/intent_rules.json | Intent rules file path |

## Security Validation

### Three-Layer Verification

To prevent LLM hallucination from bypassing DANGER-level approval:

| Node | Validation | Action |
|------|-----------|--------|
| Node 1 | Tool call verification | Detects missing tool_calls → Intent detection → Force retry |
| Node 2 | Approval flow verification | Ensures DANGER tools create pending_action |
| Node 3 | Two-phase approval validation | ApprovalStore validation → User decision (user_op_id) → Agent execution |

### Intent Detection Engine

- **Configurable**: JSON file with regex patterns (Chinese + English)
- **Runtime reload**: Call `reload_intent_rules()` to apply new rules
- **Custom path**: Set `INTENT_RULES_PATH` environment variable

### MCP Security

- **API Key verification**: MCP service supports X-API-Key header
- **Protocol version validation**: Client protocol version checked during initialization
- **Session isolation**: Each MCP client has independent session with request tracking

## Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | MVP core loop | ✅ Completed |
| Phase 2 | SQLite persistence + MCP protocol | ✅ Completed |
| Phase 3 | Real ERP adapters (SAP/Odoo) | Planned |
| Phase 4 | Permission system (RBAC) | Planned |
| Phase 5 | Workflow engine + approval flows | Planned |
| Phase 6 | RAG knowledge base | Planned |

## License

AGPL-3.0
