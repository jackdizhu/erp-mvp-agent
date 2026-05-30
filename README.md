# ERP MVP Agent

A streamlined ERP Agent system powered by LLM Tool Calling. Validate whether AI can stably drive ERP operation closed loops.

[中文版](README.zh.md)

## Overview

**Core Capability:** Natural language-driven ERP operations with intelligent tool routing and risk-based approval flows.

```
User (Natural Language)
   ↓
LLM (Intent Recognition + Tool Selection)
   ↓
Tool Layer (ERP Operations)
   ↓
Mock ERP (Data Store)
```

## Features

| Feature | Description |
|---------|-------------|
| **Natural Language ERP** | Query orders, inventory, suppliers through chat |
| **Tool Calling** | LLM-driven tool routing with 8 built-in tools |
| **Risk-Based Approval** | SAFE/CAUTION/DANGER levels with confirmation flows |
| **Session Management** | Multi-session support with localStorage persistence |
| **Error Handling** | 4-layer error model (LLM/TOOL/DATA/SYS) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React + Vite (no external UI libraries) |
| **Backend** | FastAPI (Python) |
| **AI** | LLM API (OpenAI-compatible) |
| **Data** | Mock ERP (in-memory dictionaries) |

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
cd app
pip install -r requirements.txt

# Configure environment variables
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional
export LLM_MODEL="gpt-3.5-turbo"  # or MiniMax model

# Start server
python -m main
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
  ]
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
    "id": "act_xxx",
    "summary": "Update order 123 address",
    "detail": {...}
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
  "history": [...]
}
```

## Architecture

```
/app
  main.py        # API entry point
  agent.py       # Agent core loop
  tools.py       # Tool registry & execution
  llm.py         # LLM call wrapper
  mock_erp.py    # Mock ERP data
  approval.py    # Approval flow manager
  config.py      # Risk levels, limits, configs
  errors.py      # Unified error model

/frontend/src
  App.jsx        # Root app component
  ChatPage.jsx   # Chat UI & message rendering
  ApprovalCard.jsx # Risk approval card
  SessionManager.js # Session state management
```

## Tool System

| Tool | Risk Level | Description |
|------|-----------|-------------|
| query_order | SAFE | Query single order |
| query_orders | SAFE | Batch query orders |
| query_inventory | SAFE | Check inventory |
| query_supplier | SAFE | Query supplier info |
| create_order | CAUTION | Create purchase order (limit: 5) |
| update_order | DANGER | Update order fields (requires approval) |
| cancel_order | DANGER | Cancel order (requires approval) |
| delete_order | DANGER | Delete order (requires approval, irreversible) |
| adjust_inventory | DANGER | Adjust inventory levels (requires approval) |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| OPENAI_API_KEY | - | LLM API key |
| OPENAI_BASE_URL | https://api.openai.com/v1 | Custom API endpoint |
| LLM_MODEL | gpt-3.5-turbo | Model selection |
| APPROVAL_TTL | 300 | Approval timeout (seconds) |
| APPROVAL_MAX_PENDING | 10 | Max pending approvals |
| HISTORY_WINDOW_N | 6 | Context window size |
| TOOL_LIMIT_CREATE | 5 | Max items per create |
| TOOL_LIMIT_UPDATE | 5 | Max items per update |
| TOOL_LIMIT_BATCH | 10 | Max batch query size |

## Roadmap

| Phase | Description |
|-------|-------------|
| Phase 2 | PostgreSQL persistence + LangGraph state machine |
| Phase 3 | Real ERP adapters (SAP/Odoo) |
| Phase 4 | Permission system (RBAC) |
| Phase 5 | Workflow engine + approval flows |
| Phase 6 | RAG knowledge base |

## License

AGPL-3.0
