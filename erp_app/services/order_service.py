from datetime import datetime
from erp_app.db import (
    query_order, create_order, update_order_field, update_order_status,
    delete_order, update_inventory_reserved, get_connection
)
from erp_app.seed import get_next_order_id
from erp_app.errors import (
    data_not_found, data_conflict, data_insufficient, data_invalid_supplier
)

ALLOWED_TRANSITIONS = {
    "pending": ["shipping", "cancelled"],
    "shipping": ["delivered", "cancelled"],
    "delivered": [],
    "cancelled": []
}

ALLOWED_MUTATIONS = {
    "pending": ["address", "items", "notes"],
    "shipping": ["address"],
    "delivered": [],
    "cancelled": []
}


def _can_transition(order_id: str, new_status: str) -> tuple[bool, str]:
    order = query_order(order_id)
    if not order:
        return False, f"订单{order_id}不存在"
    current = order["status"]
    if new_status not in ALLOWED_TRANSITIONS.get(current, []):
        return False, f"订单{order_id}当前状态为{current}，无法变更为{new_status}"
    return True, ""


def _can_mutate(order_id: str, field: str) -> tuple[bool, str]:
    order = query_order(order_id)
    if not order:
        return False, f"订单{order_id}不存在"
    current = order["status"]
    if current not in ALLOWED_MUTATIONS or field not in ALLOWED_MUTATIONS[current]:
        return False, f"订单{order_id}当前状态为{current}，不允许修改{field}"
    return True, ""


def create_order_service(type: str, items: list, customer: str = None,
                         supplier: str = None, address: str = None) -> dict:
    if type == "purchase" and supplier:
        sup = query_supplier_service(supplier)
        if not sup:
            raise ValueError(data_invalid_supplier(supplier))

    if type == "sales":
        for item in items:
            sku = item["sku"]
            inv = query_inventory_service(sku)
            if inv and inv["available"] < item["qty"]:
                raise ValueError(data_insufficient(
                    inv["name"], inv["available"], item["qty"], inv["unit"]
                ))

    new_id = get_next_order_id()
    today = datetime.now().strftime("%Y-%m-%d")
    total = 0
    enriched_items = []
    for item in items:
        inv = query_inventory_service(item["sku"]) or {}
        enriched_items.append({
            "sku": item["sku"],
            "name": inv.get("name", item["sku"]),
            "qty": item["qty"],
            "price": inv.get("unit_price", 0)
        })
        total += item["qty"] * inv.get("unit_price", 0)

    new_order = {
        "order_id": new_id,
        "type": type,
        "status": "pending",
        "customer": customer if type == "sales" else None,
        "total": total,
        "address": address if type == "sales" else None,
        "supplier": supplier if type == "purchase" else None,
        "created_at": today,
        "updated_at": today,
        "estimated_delivery": None,
        "cancel_reason": None,
        "notes": ""
    }
    create_order(new_order, enriched_items)

    if type == "sales":
        for item in items:
            _reserve_inventory(item["sku"], item["qty"])

    result = query_order(new_id)
    return {"success": True, "data": result}


def _reserve_inventory(sku: str, qty: int) -> None:
    inv = query_inventory_service(sku)
    if not inv:
        raise ValueError(data_not_found("商品", sku))
    if inv["available"] < qty:
        raise ValueError(data_insufficient(
            inv["name"], inv["available"], qty, inv["unit"]
        ))
    today = datetime.now().strftime("%Y-%m-%d")
    update_inventory_reserved(sku, qty, today)


def _release_inventory(sku: str, qty: int) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    update_inventory_reserved(sku, -qty, today)


def update_order_service(order_id: str, field: str, value: str) -> dict:
    order = query_order(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    ok, msg = _can_mutate(order_id, field)
    if not ok:
        raise ValueError(data_conflict("订单", order_id, msg))
    today = datetime.now().strftime("%Y-%m-%d")
    result = update_order_field(order_id, field, value, today)
    return {"success": True, "data": result}


def cancel_order_service(order_id: str, reason: str) -> dict:
    order = query_order(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    ok, msg = _can_transition(order_id, "cancelled")
    if not ok:
        raise ValueError(data_conflict("订单", order_id, msg))
    today = datetime.now().strftime("%Y-%m-%d")
    result = update_order_status(order_id, "cancelled", reason, today)
    if order["type"] == "sales":
        items = result.get("items", [])
        for item in items:
            _release_inventory(item["sku"], item["qty"])
    return {"success": True, "data": result}


def delete_order_service(order_id: str) -> dict:
    order = query_order(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    if order["status"] != "cancelled":
        raise ValueError(data_conflict("订单", order_id, "仅可删除已取消的订单"))
    delete_order(order_id)
    return {"success": True, "data": {"deleted_order_id": order_id}}


def query_supplier_service(supplier_id: str) -> dict:
    from erp_app.db import query_supplier as db_query_supplier
    return db_query_supplier(supplier_id)


def query_inventory_service(sku: str) -> dict:
    from erp_app.db import query_inventory as db_query_inventory
    return db_query_inventory(sku)
