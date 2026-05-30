from datetime import datetime
from erp_app.db import get_connection, init_db


def seed_data() -> None:
    conn = get_connection()
    cur = conn.execute("SELECT COUNT(*) as cnt FROM orders")
    if cur.fetchone()["cnt"] > 0:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    conn.executemany(
        "INSERT INTO inventory (sku, name, qty, reserved, unit, unit_price, location, reorder_point, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("iPhone-15", "iPhone 15", 60, 20, "台", 7999, "华东仓", 20, today),
            ("MacBook-Pro", "MacBook Pro 14", 30, 5, "台", 14999, "华东仓", 10, today),
        ]
    )

    conn.executemany(
        "INSERT INTO suppliers (supplier_id, name, contact, phone, lead_time_days, status) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("SUP-A", "供应商A", "王经理", "138-0000-0001", 7, "active"),
            ("SUP-B", "供应商B", "赵总", "139-0000-0002", 5, "active"),
        ]
    )

    conn.executemany(
        "INSERT INTO supplier_items (supplier_id, sku) VALUES (?, ?)",
        [
            ("SUP-A", "iPhone-15"),
            ("SUP-A", "MacBook-Pro"),
            ("SUP-B", "iPhone-15"),
        ]
    )

    conn.executemany(
        "INSERT INTO orders (order_id, type, status, customer, total, address, supplier, created_at, updated_at, estimated_delivery, cancel_reason, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("123", "sales", "shipping", "张三", 15998, "上海市浦东新区张江路88号", None,
             "2026-05-20", "2026-05-25", "2026-06-01", None, ""),
            ("124", "sales", "pending", "李四", 799900, "北京市海淀区中关村大街1号", None,
             "2026-05-22", "2026-05-22", None, None, "库存不足，等待补货"),
            ("125", "purchase", "pending", None, 75000, None, "SUP-A",
             "2026-05-28", "2026-05-28", None, None, ""),
        ]
    )

    conn.executemany(
        "INSERT INTO order_items (order_id, sku, name, qty, price) VALUES (?, ?, ?, ?, ?)",
        [
            ("123", "iPhone-15", "iPhone 15", 2, 7999),
            ("124", "iPhone-15", "iPhone 15", 100, 7999),
            ("125", "iPhone-15", "iPhone 15", 10, 7500),
        ]
    )

    conn.commit()


def get_next_order_id() -> str:
    conn = get_connection()
    cur = conn.execute("SELECT next_order_id FROM order_counter WHERE id = 1")
    row = cur.fetchone()
    next_id = str(row["next_order_id"])
    conn.execute("UPDATE order_counter SET next_order_id = ? WHERE id = 1", (row["next_order_id"] + 1,))
    conn.commit()
    return next_id
