# Design: Unified Approval Data Format

## Overview

Standardize the pending action response format across `app/approval_core.py` and `erp_mcp_service/tools.py`, with optional validation.

## Target Schema

```typescript
interface PendingAction {
  // Identification
  status: "PENDING";                         // Always "PENDING" for pending actions
  action_id: string;                         // "act_" + 8 hex chars
  
  // Tool Info
  tool: string;                              // Tool name (e.g., "update_order")
  args: Record<string, any>;                 // Tool arguments
  
  // Risk Assessment
  risk_level: "SAFE" | "WARNING" | "DANGER";  // Risk classification
  
  // Display Fields
  title: string;                             // Human-readable operation title
  summary: string;                           // Filled template summary
  description: string;                        // Concise change description
  warning: string | null;                    // Warning message or null
  
  // Structured Detail
  detail: {
    action_type: string;                     // Same as tool
    fields: Array<{name: string; value: string}>;  // Field list
    changes: Array<{                          // Field-level changes
      field: string;
      label: string;
      old: string;
      new: string;
    }>;
    irreversible: boolean;                  // Can operation be undone
  };
  
  // Timing
  expires_at: number;                         // Unix timestamp (float)
  ttl_seconds: number;                       // Seconds until expiry
}
```

## Implementation

### 1. Update erp_mcp_service/tools.py

**Current (partial)**:
```python
return {
    "status": "PENDING",
    "action_id": action.action_id,
    "approval_detail": approval_detail,  # Wrong field name
    ...
}
```

**Target**:
```python
return {
    "status": "PENDING",
    "action_id": action.action_id,
    "tool": original_name,
    "args": arguments,
    "risk_level": risk_level,
    "title": _get_operation_title(original_name),
    "summary": action_summary,  # From approval_detail
    "description": description,
    "warning": warning,
    "detail": approval_detail,  # Rename approval_detail -> detail
    "expires_at": time.time() + APPROVAL_TTL,
    "ttl_seconds": APPROVAL_TTL
}
```

### 2. Update app/approval_core.py

**Current**:
```python
pending = {
    "id": action_id,
    "tool": tool,
    "args": args,
    "messages_context": messages_context,  # Remove
    "risk_level": risk_level,
    "summary": approval_info["summary"],
    "detail": approval_info["detail"],
    "created_at": time.time(),
    "expires_at": time.time() + self._ttl_seconds,
}
```

**Target**:
```python
pending = {
    "status": "PENDING",  # Add
    "action_id": action_id,  # Rename id -> action_id
    "tool": tool,
    "args": args,
    "risk_level": risk_level,
    "title": _get_operation_title(tool),  # Add
    "summary": approval_info["summary"],
    "description": approval_info.get("description", ""),  # Add
    "warning": approval_info.get("warning"),  # Add
    "detail": approval_info["detail"],  # Keep as detail
    "expires_at": time.time() + self._ttl_seconds,
    "ttl_seconds": self._ttl_seconds,  # Add
    "messages_context": messages_context,  # Keep for app layer
}
```

### 3. Add Validation Schema

**File**: `erp_app/schemas.py` (new)

```python
from pydantic import BaseModel, Field
from typing import Optional

class ApprovalChange(BaseModel):
    field: str
    label: str
    old: str
    new: str

class ApprovalDetail(BaseModel):
    action_type: str
    fields: list[dict]
    changes: list[ApprovalChange]
    irreversible: bool

class PendingActionSchema(BaseModel):
    status: str = "PENDING"
    action_id: str
    tool: str
    args: dict
    risk_level: str
    title: str
    summary: str
    description: str
    warning: Optional[str]
    detail: ApprovalDetail
    expires_at: float
    ttl_seconds: int

def validate_pending_action(data: dict) -> tuple[bool, Optional[str]]:
    """Validate pending action format. Returns (valid, error_message)."""
    required_fields = [
        "status", "action_id", "tool", "args", "risk_level",
        "title", "summary", "description", "warning", "detail",
        "expires_at", "ttl_seconds"
    ]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if data["status"] != "PENDING":
        return False, f"Invalid status: {data['status']}"
    
    if not data["action_id"].startswith("act_"):
        return False, f"Invalid action_id format: {data['action_id']}"
    
    if data["risk_level"] not in ("SAFE", "WARNING", "DANGER"):
        return False, f"Invalid risk_level: {data['risk_level']}"
    
    if not isinstance(data["expires_at"], (int, float)):
        return False, f"expires_at must be number, got {type(data['expires_at'])}"
    
    return True, None
```

### 4. Update app/main.py Pydantic Models

```python
class PendingAction(BaseModel):
    status: str = "PENDING"
    action_id: str
    tool: str
    args: dict
    risk_level: str
    title: str
    summary: str
    description: str
    warning: Optional[str] = None
    detail: dict
    expires_at: float
    ttl_seconds: int
```

### 5. Update ApprovalDetail Fields

The `generate_approval_detail()` in `erp_app/approval_detail.py` should return:

```python
return {
    "action_type": tool_name,
    "fields": [...],
    "changes": [...],
    "irreversible": irreversible,
    # New fields
    "title": _get_operation_title(tool_name),
    "description": _generate_description(tool_name, args, old_values),
    "warning": _generate_warning(irreversible, tool_name),
}
```

Note: Some fields moved from `approval_detail` to the top-level pending action.

## Error Handling

| Error | Code | Message |
|-------|------|---------|
| Missing field | VALIDATION_ERROR | "Missing required field: {field}" |
| Invalid status | INVALID_STATUS | "status must be PENDING" |
| Invalid ID format | INVALID_ACTION_ID | "action_id must start with act_" |
| Invalid risk_level | INVALID_RISK_LEVEL | "risk_level must be SAFE/WARNING/DANGER" |
| Invalid timestamp | INVALID_TIMESTAMP | "expires_at must be numeric" |