# Spec: Unified Approval Data Format

## Purpose

Define the standardized pending action response format for approval flows.

## Definitions

### PendingAction Schema

```typescript
interface PendingAction {
  status: "PENDING";                         // Always "PENDING"
  action_id: string;                         // "act_" + 8 hex chars
  tool: string;                              // Tool name
  args: Record<string, any>;                 // Tool arguments
  risk_level: "SAFE" | "WARNING" | "DANGER"; // Risk classification
  title: string;                             // Human-readable title
  summary: string;                          // Filled template
  description: string;                       // Change description
  warning: string | null;                    // Warning or null
  detail: ApprovalDetail;                   // Structured detail
  expires_at: number;                        // Unix timestamp (float)
  ttl_seconds: number;                       // Seconds until expiry
}

interface ApprovalDetail {
  action_type: string;
  fields: Array<{name: string; value: string}>;
  changes: Array<{
    field: string;
    label: string;
    old: string;
    new: string;
  }>;
  irreversible: boolean;
}
```

## Requirements

### R1: Consistent Field Names

**Condition**: When any service returns a pending action
**Behavior**: Must include all required fields with correct names

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | Yes | Always "PENDING" |
| action_id | string | Yes | Format: act_[8 hex] |
| tool | string | Yes | Tool name |
| args | object | Yes | Tool arguments |
| risk_level | string | Yes | SAFE/WARNING/DANGER |
| title | string | Yes | Operation title |
| summary | string | Yes | Filled template |
| description | string | Yes | Change description |
| warning | string\|null | Yes | Warning message |
| detail | object | Yes | ApprovalDetail |
| expires_at | number | Yes | Unix timestamp |
| ttl_seconds | number | Yes | Seconds |

### R2: Status Value

**Condition**: When pending action is returned
**Behavior**: status field MUST be exactly "PENDING"

**Scenario: Valid pending action**
- **WHEN** pending action is created
- **THEN** `status = "PENDING"`
- **AND** `action_id = "act_abc12345"`

### R3: Action ID Format

**Condition**: When action_id is generated
**Behavior**: Must be format `act_` + 8 lowercase hex characters

**Scenario: Valid action ID**
- **WHEN** action is created
- **THEN** action_id matches `/^act_[0-9a-f]{8}$/`
- **EXAMPLE**: "act_e495052a" is valid

### R4: Risk Level Values

**Condition**: When risk_level is set
**Behavior**: Must be one of: "SAFE", "WARNING", "DANGER"

**Mapping**:
| Tool | risk_level |
|------|------------|
| query_* | SAFE |
| create_order | WARNING |
| update_order | DANGER |
| cancel_order | DANGER |
| delete_order | DANGER |
| adjust_inventory | DANGER |

### R5: Timestamp Format

**Condition**: When expires_at is set
**Behavior**: Must be Unix timestamp (float), not ISO string

**Scenario: Expires at format**
- **WHEN** pending action expires at 2026-06-01 12:00:00 UTC
- **THEN** expires_at = 1778164800.0

### R6: Detail Structure

**Condition**: When detail object is returned
**Behavior**: Must contain action_type, fields, changes, irreversible

**Scenario: Detail structure**
- **WHEN** detail is returned for update_order
- **THEN** contains:
  ```json
  {
    "action_type": "update_order",
    "fields": [...],
    "changes": [...],
    "irreversible": false
  }
  ```

### R7: Warning for Irreversible

**Condition**: When tool is irreversible
**Behavior**: warning field must contain warning message

**Scenario: Delete order warning**
- **WHEN** delete_order pending action is created
- **AND** irreversible = true
- **THEN** warning = "⚠️ 此操作不可逆，删除后将无法恢复"

### R8: Validation Function

**Condition**: When validation is enabled
**Behavior**: validate_pending_action() returns (valid, error)

**Scenario: Valid action**
- **WHEN** validate_pending_action(action) is called
- **AND** action has all required fields
- **AND** all values are correct type
- **THEN** returns (true, null)

**Scenario: Invalid action**
- **WHEN** validate_pending_action(action) is called
- **AND** action is missing "title" field
- **THEN** returns (false, "Missing required field: title")

## Compatibility

### Frontend Expectation

The `ApprovalCard.jsx` expects:
```javascript
const detail = pendingAction.detail || {};
const fields = detail.fields || [];
```

This means `detail` field name is required for frontend compatibility.

### App Layer Expectation

The `app/agent.py` expects:
```python
action = result["action"]
messages = action["messages_context"]  # App-only field
```

The `messages_context` field is app-layer specific and not required in MCP layer.