# Design: Approval Card Display Enhancement

## Overview

Enhance the approval detail structure with front-end card display fields while maintaining backward compatibility.

## Enhanced Data Structure

```typescript
interface ApprovalDetail {
  // Core identification
  action_type: string;           // "update_order", "cancel_order", etc.
  risk_level: string;            // "DANGER" | "WARNING" | "SAFE"
  
  // Card display fields
  title: string;                 // "修改订单" (human-readable operation name)
  action_summary: string;         // "修改订单 ORD-001 的 address 为 北京" (filled template)
  description: string;            // "将订单 ORD-001 的地址从'旧地址'修改为'北京'"
  warning: string | null;         // "⚠️ 此操作不可逆，请确认" or null
  
  // Structured data for forms/tables
  fields: Array<{name: string; value: string}>;  // Original field list
  changes: Array<{               // Field-level changes with old/new
    field: string;               // Field key
    label: string;               // Field label (中文)
    old: string;                 // Old value
    new: string;                 // New value
  }>;
  
  // Meta information
  irreversible: boolean;         // If operation cannot be undone
}
```

## Implementation

### 1. Template Filling Logic

```python
def _fill_summary_template(template: str, tool_name: str, args: dict) -> str:
    """Fill approvalSummary template with actual values."""
    if not template:
        return f"{_get_operation_title(tool_name)}"
    
    # Extract placeholders like {order_id}, {field}, {value}
    import re
    placeholders = re.findall(r'\{(\w+)\}', template)
    
    result = template
    for placeholder in placeholders:
        value = args.get(placeholder, '')
        result = result.replace(f'{{{placeholder}}}', str(value))
    
    return result
```

### 2. Description Generation

```python
def _generate_description(tool_name: str, args: dict, old_values: dict = None) -> str:
    """Generate concise description of the change."""
    if tool_name == "update_order":
        order_id = args.get("order_id", "")
        field = args.get("field", "")
        new_value = args.get("value", "")
        old_value = old_values.get(field, "未知") if old_values else "未知"
        return f"将订单 {order_id} 的{_get_field_label(field)}从'{old_value}'修改为'{new_value}'"
    
    elif tool_name == "cancel_order":
        order_id = args.get("order_id", "")
        reason = args.get("reason", "")
        return f"取消订单 {order_id}，原因：{reason}"
    
    elif tool_name == "delete_order":
        order_id = args.get("order_id", "")
        return f"删除已取消的订单 {order_id}"
    
    elif tool_name == "adjust_inventory":
        sku = args.get("sku", "")
        delta = args.get("delta", 0)
        return f"{'增加' if delta > 0 else '减少'}商品 {sku} 库存 {abs(delta)} 件"
    
    return f"执行 {tool_name} 操作"
```

### 3. Changes Array Building

```python
def _build_changes(tool_name: str, args: dict, old_values: dict = None) -> list:
    """Build structured changes array."""
    changes = []
    
    if tool_name == "update_order":
        field = args.get("field", "")
        changes.append({
            "field": field,
            "label": _get_field_label(field),
            "old": str(old_values.get(field, "未知")) if old_values else "未知",
            "new": str(args.get("value", ""))
        })
    
    elif tool_name == "cancel_order":
        if old_values:
            changes.append({
                "field": "status",
                "label": "订单状态",
                "old": old_values.get("status", "未知"),
                "new": "cancelled"
            })
    
    elif tool_name == "adjust_inventory":
        sku = args.get("sku", "")
        delta = args.get("delta", 0)
        current = old_values.get("qty", 0) if old_values else 0
        changes.extend([
            {"field": "qty", "label": "当前库存", "old": str(current), "new": "-"},
            {"field": "delta", "label": "调整数量", "old": "-", "new": str(delta)},
            {"field": "qty", "label": "调整后库存", "old": "-", "new": str(current + delta)},
        ])
    
    return changes
```

### 4. Warning Generation

```python
def _generate_warning(irreversible: bool, tool_name: str) -> str | None:
    """Generate warning message based on operation characteristics."""
    if not irreversible:
        return None
    
    if tool_name == "delete_order":
        return "⚠️ 此操作不可逆，删除后将无法恢复"
    elif tool_name == "cancel_order":
        return "⚠️ 取消订单后，预留库存将被释放"
    else:
        return "⚠️ 此操作不可逆，请谨慎确认"
```

### 5. Field Label Mapping

```python
FIELD_LABELS = {
    "address": "收货地址",
    "notes": "备注",
    "status": "订单状态",
    "customer": "客户名称",
    "qty": "库存数量",
}

def _get_field_label(field: str) -> str:
    """Get Chinese label for field name."""
    return FIELD_LABELS.get(field, field)
```

## File Structure Changes

```
erp_app/
└── approval_detail.py    # MOD: Add card display fields

erp_mcp_service/
├── tools.py              # MOD: Pass through new fields
└── approval_detail.py    # MOD: Update wrapper if needed
```

## Example Output

### update_order Example

**Input**: `update_order(order_id="ORD-001", field="address", value="北京")`

```json
{
  "action_type": "update_order",
  "risk_level": "DANGER",
  "title": "修改订单",
  "action_summary": "修改订单 ORD-001 的 address 为 北京",
  "description": "将订单 ORD-001 的地址从'旧地址'修改为'北京'",
  "warning": null,
  "fields": [
    {"name": "操作类型", "value": "修改订单"},
    {"name": "订单编号", "value": "ORD-001"},
    {"name": "修改字段", "value": "address"},
    {"name": "原值", "value": "旧地址"},
    {"name": "新值", "value": "北京"}
  ],
  "changes": [
    {"field": "address", "label": "地址", "old": "旧地址", "new": "北京"}
  ],
  "irreversible": false
}
```

### delete_order Example

**Input**: `delete_order(order_id="ORD-002")`

```json
{
  "action_type": "delete_order",
  "risk_level": "DANGER",
  "title": "删除订单",
  "action_summary": "删除订单 ORD-002",
  "description": "删除已取消的订单 ORD-002",
  "warning": "⚠️ 此操作不可逆，删除后将无法恢复",
  "fields": [
    {"name": "操作类型", "value": "删除订单"},
    {"name": "订单编号", "value": "ORD-002"},
    {"name": "当前状态", "value": "cancelled"}
  ],
  "changes": [],
  "irreversible": true
}
```

## Compatibility

- New fields are additive (no breaking changes)
- `fields` array structure unchanged for backward compatibility
- Frontend can progressively adopt new fields