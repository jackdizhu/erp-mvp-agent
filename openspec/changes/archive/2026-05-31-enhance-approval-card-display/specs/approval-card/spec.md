# Spec: Approval Card Display Enhancement

## Purpose

Enhance the approval detail structure with front-end card display fields.

## Overview

The approval_detail object returned from pending actions needs additional fields for front-end card rendering: title, action_summary, description, warning, changes array, and risk_level.

## Definitions

### ApprovalDetail Enhanced

```typescript
interface ApprovalDetail {
  action_type: string;              // "update_order", "cancel_order", etc.
  risk_level: string;               // "DANGER" | "WARNING" | "SAFE"
  title: string;                    // "修改订单"
  action_summary: string;           // "修改订单 ORD-001 的 address 为 北京"
  description: string;              // "将订单 ORD-001 的地址从'旧地址'修改为'北京'"
  warning: string | null;           // "⚠️ 此操作不可逆" or null
  fields: Array<{name: string; value: string}>;  // Original field list
  changes: Array<{                   // Field-level changes
    field: string;
    label: string;                  // "地址"
    old: string;
    new: string;
  }>;
  irreversible: boolean;
}
```

## Requirements

### R1: Enriched update_order Detail

**Condition**: When update_order is called and requires approval
**Behavior**: Return enhanced approval_detail with title, summary, description, and changes

**Scenario: Update order address**
- **WHEN** `update_order(order_id="ORD-001", field="address", value="北京")` is called
- **THEN** `approval_detail` contains:
  ```json
  {
    "action_type": "update_order",
    "risk_level": "DANGER",
    "title": "修改订单",
    "action_summary": "修改订单 ORD-001 的 address 为 北京",
    "description": "将订单 ORD-001 的地址从'旧地址'修改为'北京'",
    "warning": null,
    "fields": [...],
    "changes": [{"field": "address", "label": "地址", "old": "旧地址", "new": "北京"}],
    "irreversible": false
  }
  ```

### R2: Enriched cancel_order Detail

**Condition**: When cancel_order is called and requires approval
**Behavior**: Return enhanced approval_detail with title, summary, description

**Scenario: Cancel order**
- **WHEN** `cancel_order(order_id="ORD-001", reason="客户要求")` is called
- **THEN** `approval_detail` contains:
  ```json
  {
    "action_type": "cancel_order",
    "risk_level": "DANGER",
    "title": "取消订单",
    "action_summary": "取消订单 ORD-001",
    "description": "取消订单 ORD-001，原因：客户要求",
    "warning": null,
    "fields": [...],
    "changes": [{"field": "status", "label": "订单状态", "old": "pending", "new": "cancelled"}],
    "irreversible": false
  }
  ```

### R3: Enriched delete_order Detail with Warning

**Condition**: When delete_order is called and requires approval
**Behavior**: Return enhanced approval_detail with irreversible=true and warning

**Scenario: Delete order**
- **WHEN** `delete_order(order_id="ORD-002")` is called
- **THEN** `approval_detail` contains:
  ```json
  {
    "action_type": "delete_order",
    "risk_level": "DANGER",
    "title": "删除订单",
    "action_summary": "删除订单 ORD-002",
    "description": "删除已取消的订单 ORD-002",
    "warning": "⚠️ 此操作不可逆，删除后将无法恢复",
    "fields": [...],
    "changes": [],
    "irreversible": true
  }
  ```

### R4: Enriched adjust_inventory Detail

**Condition**: When adjust_inventory is called and requires approval
**Behavior**: Return enhanced approval_detail with before/after quantity changes

**Scenario: Adjust inventory**
- **WHEN** `adjust_inventory(sku="SKU-001", delta=-20, reason="盘亏")` is called
- **AND** current quantity is 100
- **THEN** `approval_detail` contains:
  ```json
  {
    "action_type": "adjust_inventory",
    "risk_level": "DANGER",
    "title": "调整库存",
    "action_summary": "调整 SKU-001 库存 -20",
    "description": "减少商品 SKU-001 库存 20 件",
    "warning": null,
    "fields": [...],
    "changes": [
      {"field": "qty", "label": "当前库存", "old": "100", "new": "-"},
      {"field": "delta", "label": "调整数量", "old": "-", "new": "-20"},
      {"field": "qty", "label": "调整后库存", "old": "-", "new": "80"}
    ],
    "irreversible": false
  }
  ```

### R5: Template Filling

**Condition**: When generating action_summary
**Behavior**: Fill `approvalSummary` template placeholders with actual argument values

**Scenario: Template with placeholders**
- **WHEN** template is `"修改订单{order_id}的{field}"`
- **AND** args are `{"order_id": "ORD-001", "field": "address"}`
- **THEN** action_summary is `"修改订单 ORD-001 的 address"`

### R6: Fallback Summary

**Condition**: When approvalSummary template is empty or not provided
**Behavior**: Generate summary from title and primary identifier

**Scenario: Missing template**
- **WHEN** approvalSummary is empty
- **AND** tool_name is `"delete_order"`
- **AND** order_id is `"ORD-003"`
- **THEN** action_summary is `"删除订单 ORD-003"`

### R7: Backward Compatibility

**Condition**: When existing code reads approval_detail
**Behavior**: `fields` array structure remains unchanged

**Scenario: Old field access**
- **WHEN** frontend accesses `approval_detail.fields`
- **THEN** structure is unchanged: `[{name: "xxx", value: "yyy"}]`

### R8: Risk Level Propagation

**Condition**: When generating approval_detail
**Behavior**: Include risk_level from tool schema

**Scenario: Risk level from schema**
- **WHEN** tool schema has `riskLevel: "DANGER"`
- **THEN** approval_detail.risk_level = "DANGER"