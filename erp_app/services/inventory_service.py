from datetime import datetime
from erp_app.db import query_inventory, update_inventory_qty
from erp_app.errors import data_not_found, data_conflict


def recalc_available(sku: str) -> None:
    pass


def adjust_inventory_service(sku: str, delta: int, reason: str) -> dict:
    item = query_inventory(sku)
    if not item:
        raise ValueError(data_not_found("商品", sku))
    new_qty = item["qty"] + delta
    if new_qty < 0:
        raise ValueError(data_conflict("库存", sku, f"调整后数量不能为负数(当前{item['qty']}, 调整{delta})"))
    today = datetime.now().strftime("%Y-%m-%d")
    result = update_inventory_qty(sku, new_qty, today)
    return {"success": True, "data": result}
