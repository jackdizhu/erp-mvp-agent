from datetime import datetime

orders = {
    "123": {
        "order_id": "123",
        "type": "sales",
        "status": "shipping",
        "customer": "张三",
        "items": [
            {"sku": "iPhone-15", "name": "iPhone 15", "qty": 2, "price": 7999}
        ],
        "total": 15998,
        "address": "上海市浦东新区张江路88号",
        "supplier": None,
        "created_at": "2026-05-20",
        "updated_at": "2026-05-25",
        "estimated_delivery": "2026-06-01",
        "cancel_reason": None,
        "notes": ""
    },
    "124": {
        "order_id": "124",
        "type": "sales",
        "status": "pending",
        "customer": "李四",
        "items": [
            {"sku": "iPhone-15", "name": "iPhone 15", "qty": 100, "price": 7999}
        ],
        "total": 799900,
        "address": "北京市海淀区中关村大街1号",
        "supplier": None,
        "created_at": "2026-05-22",
        "updated_at": "2026-05-22",
        "estimated_delivery": None,
        "cancel_reason": None,
        "notes": "库存不足，等待补货"
    },
    "125": {
        "order_id": "125",
        "type": "purchase",
        "status": "pending",
        "customer": None,
        "items": [
            {"sku": "iPhone-15", "name": "iPhone 15", "qty": 10, "price": 7500}
        ],
        "total": 75000,
        "address": None,
        "supplier": "SUP-A",
        "created_at": "2026-05-28",
        "updated_at": "2026-05-28",
        "estimated_delivery": None,
        "cancel_reason": None,
        "notes": ""
    }
}

inventory = {
    "iPhone-15": {
        "sku": "iPhone-15",
        "name": "iPhone 15",
        "qty": 60,
        "reserved": 20,
        "available": 40,
        "unit": "台",
        "unit_price": 7999,
        "location": "华东仓",
        "reorder_point": 20,
        "updated_at": "2026-05-28"
    },
    "MacBook-Pro": {
        "sku": "MacBook-Pro",
        "name": "MacBook Pro 14",
        "qty": 30,
        "reserved": 5,
        "available": 25,
        "unit": "台",
        "unit_price": 14999,
        "location": "华东仓",
        "reorder_point": 10,
        "updated_at": "2026-05-25"
    }
}

suppliers = {
    "SUP-A": {
        "supplier_id": "SUP-A",
        "name": "供应商A",
        "contact": "王经理",
        "phone": "138-0000-0001",
        "items": ["iPhone-15", "MacBook-Pro"],
        "lead_time_days": 7,
        "status": "active"
    },
    "SUP-B": {
        "supplier_id": "SUP-B",
        "name": "供应商B",
        "contact": "赵总",
        "phone": "139-0000-0002",
        "items": ["iPhone-15"],
        "lead_time_days": 5,
        "status": "active"
    }
}

order_counter = {"next_order_id": 126}

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


def recalc_available(sku: str) -> None:
    item = inventory[sku]
    item["available"] = item["qty"] - item["reserved"]
    item["updated_at"] = datetime.now().strftime("%Y-%m-%d")


def get_next_order_id() -> str:
    next_id = str(order_counter["next_order_id"])
    order_counter["next_order_id"] += 1
    return next_id


def can_transition(order_id: str, new_status: str) -> tuple[bool, str]:
    order = orders.get(order_id)
    if not order:
        return False, f"订单{order_id}不存在"
    current = order["status"]
    if new_status not in ALLOWED_TRANSITIONS.get(current, []):
        return False, f"订单{order_id}当前状态为{current}，无法变更为{new_status}"
    return True, ""


def can_mutate(order_id: str, field: str) -> tuple[bool, str]:
    order = orders.get(order_id)
    if not order:
        return False, f"订单{order_id}不存在"
    current = order["status"]
    if current not in ALLOWED_MUTATIONS or field not in ALLOWED_MUTATIONS[current]:
        return False, f"订单{order_id}当前状态为{current}，不允许修改{field}"
    return True, ""


def reserve_inventory(sku: str, qty: int) -> tuple[bool, str]:
    item = inventory.get(sku)
    if not item:
        return False, f"商品{sku}不存在"
    if item["available"] < qty:
        return False, f"{item['name']}库存不足，当前可用{item['available']}{item['unit']}"
    item["reserved"] += qty
    recalc_available(sku)
    return True, ""


def release_inventory(sku: str, qty: int) -> None:
    item = inventory.get(sku)
    if item:
        item["reserved"] = max(0, item["reserved"] - qty)
        recalc_available(sku)
