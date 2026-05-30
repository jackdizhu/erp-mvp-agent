from erp_app.db import query_order, query_inventory


def generate_approval_detail(tool_name: str, args: dict) -> dict:
    fields = []
    irreversible = False

    if tool_name == "update_order":
        order = query_order(args.get("order_id", ""))
        fields = [
            {"name": "操作类型", "value": "修改订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "修改字段", "value": args.get("field", "")},
            {"name": "原值", "value": str(order.get(args.get("field", ""), "")) if order else "未知"},
            {"name": "新值", "value": args.get("value", "")},
        ]
    elif tool_name == "cancel_order":
        order = query_order(args.get("order_id", ""))
        fields = [
            {"name": "操作类型", "value": "取消订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "当前状态", "value": order.get("status", "") if order else "未知"},
            {"name": "取消原因", "value": args.get("reason", "")},
        ]
    elif tool_name == "delete_order":
        order = query_order(args.get("order_id", ""))
        fields = [
            {"name": "操作类型", "value": "删除订单"},
            {"name": "订单编号", "value": args.get("order_id", "")},
            {"name": "当前状态", "value": order.get("status", "") if order else "未知"},
        ]
        irreversible = True
    elif tool_name == "adjust_inventory":
        item = query_inventory(args.get("sku", ""))
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

    return {
        "action_type": tool_name,
        "fields": fields,
        "irreversible": irreversible
    }
