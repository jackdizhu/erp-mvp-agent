# Design: MCP Tool Approval Flow

## Overview

Implements human-in-the-loop approval for high-risk ERP operations through MCP protocol extension.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP Approval Flow                                │
└─────────────────────────────────────────────────────────────────────┘

  LLM                           MCP Service                    Storage
   │                                 │                              │
   │  tools/list                     │                              │
   │────────────────────────────────▶│                              │
   │                                 │                              │
   │  { tools: [                     │                              │
   │    { name: "mcp_update_order", │                              │
   │      metadata: {               │                              │
   │        riskLevel: "DANGER",    │                              │
   │        requiresApproval: true  │                              │
   │      }                         │                              │
   │    }                           │                              │
   │  ]}                            │                              │
   │                                 │                              │
   │  tools/call {name, args}        │                              │
   │────────────────────────────────▶│                              │
   │                                 │  ✋ Check metadata            │
   │                                 │  ✋ Create pending_action     │
   │                                 │─────────────────────────────▶│
   │                                 │                              │
   │  { status: "PENDING",           │                              │
   │    action_id: "act_xxx",        │                              │
   │    approval_detail: {...} }     │                              │
   │◀────────────────────────────────│                              │
   │                                 │                              │
   │  [User approves via UI]         │                              │
   │                                 │                              │
   │  tools/call {                   │                              │
   │    name: "mcp_confirm_approval",│                             │
   │    action_id: "act_xxx",        │                              │
   │    approved: true               │                              │
   │  }                              │                              │
   │────────────────────────────────▶│                              │
   │                                 │  ✋ Lookup pending_action     │
   │                                 │  ✋ Execute original tool     │
   │                                 │─────────────────────────────▶│
   │  { success: true, data: {...} }  │                              │
   │◀────────────────────────────────│                              │
```

## File Structure

```
erp_mcp_service/
├── config.py              # NEW: APPROVAL_TTL, APPROVAL_MAX_PENDING
├── approval_manager.py    # NEW: PendingAction class, storage, TTL
├── approval_detail.py     # NEW: Thin wrapper of erp_app/approval_detail
├── tools.py               # MOD: list_tools() adds metadata, call_tool() checks approval
└── main.py                # MOD: Register mcp_confirm_approval tool

erp_app/
└── tools.py               # MOD: TOOL_SCHEMAS adds riskLevel, requiresApproval, etc.
```

## Data Structures

### Tool Metadata (TOOL_SCHEMAS extension)

```python
{
    "name": "update_order",
    "description": "修改订单的指定字段",
    "riskLevel": "DANGER",           # SAFE | WARNING | DANGER
    "requiresApproval": True,
    "irreversible": False,
    "approvalSummary": "修改订单{order_id}的{field}",
    "inputSchema": { ... }
}
```

### Pending Action

```python
@dataclass
class PendingAction:
    action_id: str           # "act_" + uuid
    tool_name: str           # Original tool name (without mcp_ prefix)
    arguments: dict          # Original tool arguments
    risk_level: str          # DANGER, WARNING, SAFE
    approval_detail: dict    # From approval_detail.py
    created_at: float        # time.time()
    ttl: int                # Seconds until expiration
    status: str              # pending | approved | rejected | expired
```

### Pending Response (from tools/call)

```python
{
    "status": "PENDING",
    "action_id": "act_abc123",
    "risk_level": "DANGER",
    "approval_detail": {
        "action_type": "update_order",
        "fields": [
            {"name": "操作类型", "value": "修改订单"},
            {"name": "订单编号", "value": "ORD-001"},
            {"name": "修改字段", "value": "address"},
            {"name": "原值", "value": "旧地址"},
            {"name": "新值", "value": "新地址"}
        ],
        "irreversible": False
    },
    "expires_at": "2026-05-31T12:05:00Z",
    "ttl_seconds": 300
}
```

### mcp_confirm_approval Schema

```python
{
    "name": "mcp_confirm_approval",
    "description": "确认或拒绝待审批的操作",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action_id": {
                "type": "string",
                "description": "审批动作ID (来自pending状态的action_id)"
            },
            "approved": {
                "type": "boolean",
                "description": "true=批准执行, false=拒绝并取消"
            }
        },
        "required": ["action_id", "approved"]
    }
}
```

### Confirm Response

```python
# Success (approved)
{
    "success": True,
    "action_id": "act_abc123",
    "executed": True,
    "result": { ... }  # Original tool execution result
}

# Success (rejected)
{
    "success": True,
    "action_id": "act_abc123",
    "executed": False,
    "message": "操作已取消"
}

# Error (expired)
{
    "success": False,
    "error": "APPROVAL_EXPIRED",
    "message": "审批已过期，请重新发起操作"
}
```

## Implementation Details

### 1. Tool Metadata Extension (erp_app/tools.py)

Add to TOOL_SCHEMAS for DANGER tools:

```python
{
    "name": "update_order",
    "riskLevel": "DANGER",
    "requiresApproval": True,
    "irreversible": False,
    "approvalSummary": "修改订单{order_id}的{field}为{value}",
    ...
}
{
    "name": "cancel_order",
    "riskLevel": "DANGER",
    "requiresApproval": True,
    "irreversible": False,
    "approvalSummary": "取消订单{order_id}",
    ...
}
{
    "name": "delete_order",
    "riskLevel": "DANGER",
    "requiresApproval": True,
    "irreversible": True,
    "approvalSummary": "删除订单{order_id}",
    ...
}
{
    "name": "adjust_inventory",
    "riskLevel": "DANGER",
    "requiresApproval": True,
    "irreversible": False,
    "approvalSummary": "调整{sku}库存{delta}",
    ...
}
```

SAFE tools (query_*, create_order) keep default values.

### 2. Metadata Aggregation (erp_mcp_service/tools.py)

```python
def list_tools() -> List[Dict[str, Any]]:
    tools = []
    for schema in TOOL_SCHEMAS:
        tool = {
            "name": f"mcp_{schema['name']}",
            "description": schema.get("description", ""),
            "inputSchema": schema.get("inputSchema", {}),
            "metadata": {
                "riskLevel": schema.get("riskLevel", "SAFE"),
                "requiresApproval": schema.get("requiresApproval", False),
                "irreversible": schema.get("irreversible", False),
                "approvalSummary": schema.get("approvalSummary", ""),
            }
        }
        tools.append(tool)
    
    # Add mcp_confirm_approval tool
    tools.append({
        "name": "mcp_confirm_approval",
        "description": "确认或拒绝待审批的操作",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_id": {"type": "string"},
                "approved": {"type": "boolean"}
            },
            "required": ["action_id", "approved"]
        },
        "metadata": {
            "riskLevel": "SAFE",
            "requiresApproval": False,
            "irreversible": False
        }
    })
    
    return tools
```

### 3. Approval Manager (erp_mcp_service/approval_manager.py)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid
import time
from threading import Lock

@dataclass
class PendingAction:
    action_id: str
    tool_name: str
    arguments: dict
    risk_level: str
    approval_detail: dict
    created_at: float
    ttl: int
    status: str = "pending"

class ApprovalManager:
    def __init__(self, default_ttl: int = 300, max_pending: int = 10):
        self._pending: Dict[str, PendingAction] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self.max_pending = max_pending
    
    def create(self, tool_name: str, arguments: dict, 
               risk_level: str, approval_detail: dict,
               ttl: int = None) -> PendingAction:
        with self._lock:
            self._cleanup_expired()
            if len(self._pending) >= self.max_pending:
                raise ValueError("MAX_PENDING_EXCEEDED")
            
            action = PendingAction(
                action_id=f"act_{uuid.uuid4().hex[:12]}",
                tool_name=tool_name,
                arguments=arguments,
                risk_level=risk_level,
                approval_detail=approval_detail,
                created_at=time.time(),
                ttl=ttl or self.default_ttl
            )
            self._pending[action.action_id] = action
            return action
    
    def confirm(self, action_id: str) -> tuple[bool, Any]:
        with self._lock:
            action = self._pending.get(action_id)
            if not action:
                return False, "ACTION_NOT_FOUND"
            if action.status != "pending":
                return False, f"ACTION_ALREADY_{action.status.upper()}"
            if self._is_expired(action):
                action.status = "expired"
                return False, "APPROVAL_EXPIRED"
            
            action.status = "approved"
            return True, None
    
    def reject(self, action_id: str) -> tuple[bool, str]:
        with self._lock:
            action = self._pending.get(action_id)
            if not action:
                return False, "ACTION_NOT_FOUND"
            if action.status != "pending":
                return False, f"ACTION_ALREADY_{action.status.upper()}"
            
            action.status = "rejected"
            return True, None
    
    def get(self, action_id: str) -> Optional[PendingAction]:
        return self._pending.get(action_id)
    
    def _is_expired(self, action: PendingAction) -> bool:
        return (time.time() - action.created_at) > action.ttl
    
    def _cleanup_expired(self):
        expired = [
            aid for aid, action in self._pending.items()
            if action.status == "pending" and self._is_expired(action)
        ]
        for aid in expired:
            self._pending[aid].status = "expired"
    
    def cleanup(self):
        with self._lock:
            self._cleanup_expired()
```

### 4. Approval Detail Wrapper (erp_mcp_service/approval_detail.py)

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from erp_app.approval_detail import generate_approval_detail

def get_approval_detail(tool_name: str, args: dict) -> dict:
    return generate_approval_detail(tool_name, args)
```

### 5. Approval Interception (erp_mcp_service/tools.py)

```python
from .approval_manager import approval_manager
from .approval_detail import get_approval_detail

def call_tool(name: str, arguments: dict) -> dict:
    original_name = name[4:] if name.startswith("mcp_") else name
    
    # Special handling for confirm_approval
    if original_name == "confirm_approval":
        return _handle_confirm_approval(arguments)
    
    # Check if approval is required
    requires_approval = _check_requires_approval(original_name)
    
    if requires_approval:
        # Get tool schema for risk level
        risk_level = _get_risk_level(original_name)
        
        # Generate approval detail
        try:
            approval_detail = get_approval_detail(original_name, arguments)
        except Exception:
            approval_detail = {
                "action_type": original_name,
                "fields": [],
                "irreversible": False
            }
        
        # Calculate expiration
        from config import APPROVAL_TTL
        from datetime import datetime, timezone
        expires_at = datetime.fromtimestamp(
            time.time() + APPROVAL_TTL, tz=timezone.utc
        ).isoformat()
        
        # Create pending action
        action = approval_manager.create(
            tool_name=original_name,
            arguments=arguments,
            risk_level=risk_level,
            approval_detail=approval_detail,
            ttl=APPROVAL_TTL
        )
        
        return {
            "status": "PENDING",
            "action_id": action.action_id,
            "risk_level": risk_level,
            "approval_detail": approval_detail,
            "expires_at": expires_at,
            "ttl_seconds": APPROVAL_TTL
        }
    
    # Execute directly (no approval needed)
    return execute_tool(original_name, arguments)

def _handle_confirm_approval(arguments: dict) -> dict:
    action_id = arguments.get("action_id")
    approved = arguments.get("approved", False)
    
    if not action_id:
        raise ValueError("MISSING_ACTION_ID")
    
    action = approval_manager.get(action_id)
    if not action:
        return {
            "success": False,
            "error": "ACTION_NOT_FOUND",
            "message": f"审批动作 {action_id} 不存在或已过期"
        }
    
    if action.status != "pending":
        return {
            "success": False,
            "error": f"ACTION_ALREADY_{action.status.upper()}",
            "message": f"审批动作已是 {action.status} 状态"
        }
    
    # Check expiration
    if time.time() - action.created_at > action.ttl:
        action.status = "expired"
        return {
            "success": False,
            "error": "APPROVAL_EXPIRED",
            "message": "审批已过期，请重新发起操作"
        }
    
    if approved:
        # Execute original tool
        success, error = approval_manager.confirm(action_id)
        if not success:
            return {
                "success": False,
                "error": error,
                "message": f"执行失败: {error}"
            }
        
        try:
            result = execute_tool(action.tool_name, action.arguments)
            return {
                "success": True,
                "action_id": action_id,
                "executed": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": "EXECUTION_FAILED",
                "message": f"执行失败: {str(e)}"
            }
    else:
        # Reject/cancel
        success, error = approval_manager.reject(action_id)
        return {
            "success": True,
            "action_id": action_id,
            "executed": False,
            "message": "操作已取消"
        }

def _check_requires_approval(tool_name: str) -> bool:
    for schema in TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema.get("requiresApproval", False)
    return False

def _get_risk_level(tool_name: str) -> str:
    for schema in TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema.get("riskLevel", "SAFE")
    return "SAFE"
```

### 6. Config Extension (erp_mcp_service/config.py)

```python
APPROVAL_TTL = 300          # 5 minutes
APPROVAL_MAX_PENDING = 10   # Max concurrent pending actions
```

## Error Codes

| Code | Meaning | HTTP Status |
|------|---------|-------------|
| ACTION_NOT_FOUND | action_id 不存在 | N/A (in response) |
| ACTION_ALREADY_PENDING | 已是 pending 状态 | N/A |
| ACTION_ALREADY_APPROVED | 已被批准 | N/A |
| ACTION_ALREADY_REJECTED | 已被拒绝 | N/A |
| APPROVAL_EXPIRED | 审批已过期 | N/A |
| MAX_PENDING_EXCEEDED | 待审批数量超限 | N/A |
| MISSING_ACTION_ID | 缺少 action_id | N/A |