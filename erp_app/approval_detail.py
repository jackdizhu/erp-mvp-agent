import re
from erp_app.db import query_order, query_inventory

FIELD_LABELS = {
    "address": "收货地址",
    "notes": "备注",
    "status": "订单状态",
    "customer": "客户名称",
}

OPERATION_TITLES = {
    "update_order": "修改订单",
    "cancel_order": "取消订单",
    "delete_order": "删除订单",
    "adjust_inventory": "调整库存",
}


def _get_field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def _get_operation_title(tool_name: str) -> str:
    return OPERATION_TITLES.get(tool_name, tool_name)


def _fill_summary_template(template: str, tool_name: str, args: dict) -> str:
    if not template:
        return f"{_get_operation_title(tool_name)}"
    placeholders = re.findall(r'\{(\w+)\}', template)
    result = template
    for placeholder in placeholders:
        value = args.get(placeholder, '')
        result = result.replace(f'{{{placeholder}}}', str(value))
    return result


def _generate_description(tool_name: str, args: dict, old_values: dict = None) -> str:
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


def _build_changes(tool_name: str, args: dict, old_values: dict = None) -> list:
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
    elif tool_name == "delete_order":
        pass
    elif tool_name == "adjust_inventory":
        delta = args.get("delta", 0)
        current = old_values.get("qty", 0) if old_values else 0
        changes.extend([
            {"field": "qty", "label": "当前库存", "old": str(current), "new": "-"},
            {"field": "delta", "label": "调整数量", "old": "-", "new": str(delta)},
            {"field": "qty", "label": "调整后库存", "old": "-", "new": str(current + delta)},
        ])
    return changes


def _generate_warning(irreversible: bool, tool_name: str):
    if not irreversible:
        return None
    if tool_name == "delete_order":
        return "⚠️ 此操作不可逆，删除后将无法恢复"
    elif tool_name == "cancel_order":
        return "⚠️ 取消订单后，预留库存将被释放"
    else:
        return "⚠️ 此操作不可逆，请谨慎确认"


def generate_approval_detail(tool_name: str, args: dict) -> dict:
    from erp_app.tools import TOOL_SCHEMAS
    
    schema = next((s for s in TOOL_SCHEMAS if s["name"] == tool_name), {})
    risk_level = schema.get("riskLevel", "SAFE")
    approval_summary_template = schema.get("approvalSummary", "")
    irreversible = schema.get("irreversible", False)
    
    old_values = None
    if tool_name in ("update_order", "cancel_order", "delete_order"):
        old_values = query_order(args.get("order_id", ""))
    elif tool_name == "adjust_inventory":
        old_values = query_inventory(args.get("sku", ""))
    
    fields = []
    if tool_name == "update_order":
        fields = [
            {"name": "操作类型", "value": "修改订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "修改字段", "value": args.get("field", "")},
            {"name": "原值", "value": str(old_values.get(args.get("field", ""), "")) if old_values else "未知"},
            {"name": "新值", "value": args.get("value", "")},
        ]
    elif tool_name == "cancel_order":
        fields = [
            {"name": "操作类型", "value": "取消订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "当前状态", "value": old_values.get("status", "") if old_values else "未知"},
            {"name": "取消原因", "value": args.get("reason", "")},
        ]
    elif tool_name == "delete_order":
        fields = [
            {"name": "操作类型", "value": "删除订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "当前状态", "value": old_values.get("status", "") if old_values else "未知"},
        ]
    elif tool_name == "adjust_inventory":
        item = old_values
        current_qty = item.get("qty", 0) if item else 0
        delta = args.get("delta", 0)
        fields = [
            {"name": "操作类型", "value": "调整库存"},
            {"name": "商品名称", "value": item.get("name", args.get("sku", "")) if item else args.get("sku", "")},
            {"name": "当前库存", "value": str(current_qty)},
            {"name": "调整数量", "value": str(delta)},
            {"name": "调整后库存", "value": str(current_qty + delta)},
            {"name": "调整原因", "value": args.get("reason", "")},
        ]
    
    action_summary = _fill_summary_template(approval_summary_template, tool_name, args)
    description = _generate_description(tool_name, args, old_values)
    warning = _generate_warning(irreversible, tool_name)
    changes = _build_changes(tool_name, args, old_values)
    title = _get_operation_title(tool_name)
    
    return {
        "action_type": tool_name,
        "risk_level": risk_level,
        "title": title,
        "action_summary": action_summary,
        "description": description,
        "warning": warning,
        "fields": fields,
        "changes": changes,
        "irreversible": irreversible
    }