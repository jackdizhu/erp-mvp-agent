# Spec: MCP Tool Approval

## Purpose

Add approval flow to MCP service for high-risk ERP operations using Tool Metadata extension.

## Overview

Extend Tool Schemas with risk metadata. Intercept high-risk tool calls, return pending status with approval details. Confirm or reject via mcp_confirm_approval tool.

## Definitions

### Tool Metadata

```typescript
interface ToolMetadata {
  riskLevel: "SAFE" | "WARNING" | "DANGER";
  requiresApproval: boolean;
  irreversible: boolean;
  approvalSummary: string;  // Template with {param} placeholders
}
```

### Pending Action

```typescript
interface PendingAction {
  action_id: string;         // "act_" + 12 hex chars
  tool_name: string;         // Original tool name
  arguments: dict;          // Original tool arguments
  risk_level: string;
  approval_detail: {
    action_type: string;
    fields: Array<{name: string; value: string}>;
    irreversible: boolean;
  };
  created_at: float;        // Unix timestamp
  ttl: int;                 // Seconds
  status: "pending" | "approved" | "rejected" | "expired";
}
```

### Pending Response

```typescript
interface PendingResponse {
  status: "PENDING";
  action_id: string;
  risk_level: string;
  approval_detail: dict;
  expires_at: string;        // ISO timestamp
  ttl_seconds: int;
}
```

## Requirements

### R1: Tool Schema Extension

**Condition**: When DANGER-level tools are defined in erp_app/tools.py
**Behavior**: TOOL_SCHEMAS must include riskLevel, requiresApproval, irreversible, approvalSummary fields

| Tool | riskLevel | requiresApproval | irreversible |
|------|-----------|------------------|--------------|
| query_order | SAFE | false | false |
| query_orders | SAFE | false | false |
| query_inventory | SAFE | false | false |
| query_supplier | SAFE | false | false |
| create_order | WARNING | false | false |
| update_order | DANGER | true | false |
| cancel_order | DANGER | true | false |
| delete_order | DANGER | true | true |
| adjust_inventory | DANGER | true | false |

### R2: Metadata Propagation

**Condition**: When tools/list is called
**Behavior**: Response includes metadata block for each tool

```json
{
  "tools": [{
    "name": "mcp_update_order",
    "metadata": {
      "riskLevel": "DANGER",
      "requiresApproval": true,
      "irreversible": false,
      "approvalSummary": "修改订单{order_id}的{field}"
    }
  }]
}
```

### R3: Approval Interception

**Condition**: When tools/call is invoked with requiresApproval=true tool
**Behavior**: Return pending response instead of executing tool

**Scenario: DANGER tool called**
- **WHEN** LLM calls `mcp_update_order(order_id="ORD-001", field="address", value="北京")`
- **THEN** system returns:
  ```json
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
        {"name": "新值", "value": "北京"}
      ],
      "irreversible": false
    },
    "expires_at": "2026-05-31T12:05:00Z",
    "ttl_seconds": 300
  }
  ```

### R4: Approval Confirmation

**Condition**: When mcp_confirm_approval is called with approved=true
**Behavior**: Execute original tool and return result

**Scenario: Approved action executed**
- **WHEN** `mcp_confirm_approval(action_id="act_abc123", approved=true)` is called
- **AND** action status is "pending"
- **AND** action is not expired
- **THEN** execute original tool, return result:
  ```json
  {
    "success": true,
    "action_id": "act_abc123",
    "executed": true,
    "result": {"success": true, "data": {...}}
  }
  ```

**Scenario: Expired action confirmed**
- **WHEN** action TTL has elapsed
- **THEN** return:
  ```json
  {
    "success": false,
    "error": "APPROVAL_EXPIRED",
    "message": "审批已过期，请重新发起操作"
  }
  ```

### R5: Approval Rejection

**Condition**: When mcp_confirm_approval is called with approved=false
**Behavior**: Mark action as rejected, return cancellation message

**Scenario: Action rejected**
- **WHEN** `mcp_confirm_approval(action_id="act_abc123", approved=false)` is called
- **THEN** return:
  ```json
  {
    "success": true,
    "action_id": "act_abc123",
    "executed": false,
    "message": "操作已取消"
  }
  ```

### R6: TTL Expiration

**Condition**: When pending action exceeds TTL
**Behavior**: Mark action as expired, return error on confirm attempt

**Scenario: Expired action lookup**
- **WHEN** get(action_id) is called for expired pending action
- **THEN** action.status = "expired"

### R7: Cleanup on Access

**Condition**: When ApprovalManager creates or accesses actions
**Behavior**: Remove expired actions before operation

### R8: mcp_confirm_approval Registration

**Condition**: When tools/list is called
**Behavior**: Include mcp_confirm_approval in tool list with SAFE riskLevel

### R9: Multiple Pending Actions

**Condition**: When multiple DANGER tools are called in sequence
**Behavior**: Each creates independent pending action with unique action_id

**Scenario: Two pending actions**
- **WHEN** LLM calls update_order and cancel_order
- **THEN** two pending actions created with different action_ids

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| APPROVAL_TTL | 300 | Seconds until pending action expires |
| APPROVAL_MAX_PENDING | 10 | Maximum concurrent pending actions |

## Error Codes

| Code | Meaning |
|------|---------|
| ACTION_NOT_FOUND | action_id does not exist |
| ACTION_ALREADY_PENDING | Action already in pending state |
| ACTION_ALREADY_APPROVED | Action already approved |
| ACTION_ALREADY_REJECTED | Action already rejected |
| APPROVAL_EXPIRED | Action TTL exceeded |
| MAX_PENDING_EXCEEDED | Too many pending actions |
| MISSING_ACTION_ID | action_id parameter missing |