import sqlite3
import os
import threading
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "erp.db")

_local = threading.local()
_init_lock = threading.Lock()


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        with _init_lock:
            _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    _ensure_dir()
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            customer TEXT,
            total REAL DEFAULT 0,
            address TEXT,
            supplier TEXT,
            created_at TEXT,
            updated_at TEXT,
            estimated_delivery TEXT,
            cancel_reason TEXT,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            price REAL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );

        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 0,
            reserved INTEGER NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT '台',
            unit_price REAL DEFAULT 0,
            location TEXT,
            reorder_point INTEGER DEFAULT 0,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            lead_time_days INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS supplier_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );

        CREATE TABLE IF NOT EXISTS order_counter (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            next_order_id INTEGER NOT NULL DEFAULT 126
        );

        INSERT OR IGNORE INTO order_counter (id, next_order_id) VALUES (1, 126);
    """)
    conn.commit()


def close_db() -> None:
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def query_order(order_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cur.fetchone()
    if not order:
        return None
    result = _row_to_dict(order)
    items_cur = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    result["items"] = [_row_to_dict(r) for r in items_cur.fetchall()]
    return result


def query_orders_batch(order_ids: list) -> dict:
    conn = get_connection()
    results = {}
    for oid in order_ids:
        cur = conn.execute("SELECT order_id, status, type FROM orders WHERE order_id = ?", (oid,))
        row = cur.fetchone()
        if row:
            results[oid] = {"status": row["status"], "type": row["type"]}
        else:
            results[oid] = {"status": "not_found"}
    return results


def create_order(order: dict, items: list) -> dict:
    conn = get_connection()
    conn.execute(
        """INSERT INTO orders (order_id, type, status, customer, total, address, supplier,
           created_at, updated_at, estimated_delivery, cancel_reason, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order["order_id"], order["type"], order["status"], order.get("customer"),
         order["total"], order.get("address"), order.get("supplier"),
         order["created_at"], order["updated_at"], order.get("estimated_delivery"),
         order.get("cancel_reason"), order.get("notes", ""))
    )
    for item in items:
        conn.execute(
            "INSERT INTO order_items (order_id, sku, name, qty, price) VALUES (?, ?, ?, ?, ?)",
            (order["order_id"], item["sku"], item["name"], item["qty"], item["price"])
        )
    conn.commit()
    return order


def update_order_field(order_id: str, field: str, value: str, updated_at: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute(f"UPDATE orders SET {field} = ?, updated_at = ? WHERE order_id = ?",
                 (value, updated_at, order_id))
    conn.commit()
    return query_order(order_id)


def update_order_status(order_id: str, new_status: str, cancel_reason: Optional[str], updated_at: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute("UPDATE orders SET status = ?, cancel_reason = ?, updated_at = ? WHERE order_id = ?",
                 (new_status, cancel_reason, updated_at, order_id))
    conn.commit()
    return query_order(order_id)


def delete_order(order_id: str) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
    conn.commit()
    return True


def query_inventory(sku: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.execute("SELECT *, (qty - reserved) as available FROM inventory WHERE sku = ?", (sku,))
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def update_inventory_qty(sku: str, new_qty: int, updated_at: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute("UPDATE inventory SET qty = ?, updated_at = ? WHERE sku = ?",
                 (new_qty, updated_at, sku))
    conn.commit()
    return query_inventory(sku)


def update_inventory_reserved(sku: str, delta: int, updated_at: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute("UPDATE inventory SET reserved = MAX(0, reserved + ?), updated_at = ? WHERE sku = ?",
                 (delta, updated_at, sku))
    conn.commit()
    return query_inventory(sku)


def query_supplier(supplier_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    row = cur.fetchone()
    if not row:
        return None
    result = _row_to_dict(row)
    items_cur = conn.execute("SELECT sku FROM supplier_items WHERE supplier_id = ?", (supplier_id,))
    result["items"] = [r["sku"] for r in items_cur.fetchall()]
    return result


def query_all_suppliers() -> list:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM suppliers")
    suppliers = []
    for row in cur.fetchall():
        s = _row_to_dict(row)
        items_cur = conn.execute("SELECT sku FROM supplier_items WHERE supplier_id = ?", (s["supplier_id"],))
        s["items"] = [r["sku"] for r in items_cur.fetchall()]
        suppliers.append(s)
    return suppliers
