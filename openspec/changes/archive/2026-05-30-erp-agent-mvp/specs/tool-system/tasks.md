# Tool System — Tasks

> Spec: [specs/tool-system/spec.md](spec.md)
> Files: `/app/tools.py`, `/app/config.py`

---

## 1. 配置系统 (config.py)

- [x] 1.1 实现 TOOL_RISK_LEVELS 风险分级映射
- [x] 1.2 实现 TOOL_LIMITS 限额配置
- [x] 1.3 实现 APPROVAL_CONFIG 审批配置
- [x] 1.4 实现 ACTION_SUMMARIES 摘要模板
- [x] 1.5 实现 HISTORY_WINDOW 历史窗口配置

```python
import os

TOOL_RISK_LEVELS = {
    "query_order": "SAFE",
    "query_orders": "SAFE",
    "query_inventory": "SAFE",
    "query_supplier": "SAFE",
    "create_order": "CAUTION",
    "update_order": "DANGER",
    "cancel_order": "DANGER",
    "delete_order": "DANGER",
    "adjust_inventory": "DANGER",
}

TOOL_LIMITS = {
    "create_order": {"max_items": int(os.getenv("TOOL_LIMIT_CREATE", "5"))},
    "delete_order": {"max_items": 1},
    "update_order": {"max_items": int(os.getenv("TOOL_LIMIT_UPDATE", "5"))},
    "query_orders": {"max_batch": int(os.getenv("TOOL_LIMIT_BATCH", "10"))},
}

APPROVAL_CONFIG = {
    "ttl_seconds": int(os.getenv("APPROVAL_TTL", "300")),
    "max_pending": int(os.getenv("APPROVAL_MAX_PENDING", "10")),
}

ACTION_SUMMARIES = {
    "update_order": "修改订单{order_id}的{field}",
    "cancel_order": "取消订单{order_id}",
    "delete_order": "删除订单{order_id}",
    "adjust_inventory": "调整{sku}库存数量",
}

HISTORY_WINDOW = {
    "default_n": int(os.getenv("HISTORY_WINDOW_N", "6")),
}
```

## 2. Tool Schema 定义 (tools.py)

- [x] 2.1 实现 8 个 Tool 的 OpenAI function calling 格式 Schema

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单ID查询订单详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单编号"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_orders",
            "description": "批量查询多个订单的状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "订单编号列表"
                    }
                },
                "required": ["order_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_inventory",
            "description": "根据商品SKU查询库存信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "商品SKU编号"
                    }
                },
                "required": ["sku"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_supplier",
            "description": "根据供应商ID查询供应商信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "supplier_id": {
                        "type": "string",
                        "description": "供应商编号"
                    }
                },
                "required": ["supplier_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "创建销售订单或采购订单",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["sales", "purchase"],
                        "description": "订单类型: sales=销售订单, purchase=采购订单"
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string", "description": "商品SKU"},
                                "qty": {"type": "integer", "description": "数量"}
                            },
                            "required": ["sku", "qty"]
                        },
                        "description": "订单商品列表"
                    },
                    "customer": {
                        "type": "string",
                        "description": "客户名称(销售订单必填)"
                    },
                    "supplier": {
                        "type": "string",
                        "description": "供应商编号(采购订单必填)"
                    },
                    "address": {
                        "type": "string",
                        "description": "收货地址(销售订单)"
                    }
                },
                "required": ["type", "items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_order",
            "description": "修改订单的指定字段",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单编号"
                    },
                    "field": {
                        "type": "string",
                        "description": "要修改的字段名(如address, notes等)"
                    },
                    "value": {
                        "type": "string",
                        "description": "新的字段值"
                    }
                },
                "required": ["order_id", "field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "取消订单并释放预留库存",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单编号"
                    },
                    "reason": {
                        "type": "string",
                        "description": "取消原因"
                    }
                },
                "required": ["order_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_order",
            "description": "删除已取消的订单(仅限cancelled状态)",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单编号"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_inventory",
            "description": "调整商品库存数量(正数入库/负数出库)",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "商品SKU编号"
                    },
                    "delta": {
                        "type": "integer",
                        "description": "调整数量(正数入库/负数出库)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "调整原因"
                    }
                },
                "required": ["sku", "delta", "reason"]
            }
        }
    }
]
```

## 3. SAFE Tool 实现

- [x] 3.1 实现 query_order
- [x] 3.2 实现 query_orders
- [x] 3.3 实现 query_inventory
- [x] 3.4 实现 query_supplier

```python
from app.mock_erp import orders, inventory, suppliers
from app.errors import data_not_found

def query_order(order_id: str) -> dict:
    order = orders.get(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    return {"success": True, "data": order}

def query_orders(order_ids: list) -> dict:
    max_batch = TOOL_LIMITS["query_orders"]["max_batch"]
    if len(order_ids) > max_batch:
        raise ValueError(tool_limit("query_orders", max_batch, len(order_ids)))
    results = {}
    for oid in order_ids:
        order = orders.get(oid)
        if order:
            results[oid] = {"status": order["status"], "type": order["type"]}
        else:
            results[oid] = {"status": "not_found"}
    return {"success": True, "data": results}

def query_inventory(sku: str) -> dict:
    item = inventory.get(sku)
    if not item:
        raise ValueError(data_not_found("商品", sku))
    return {"success": True, "data": item}

def query_supplier(supplier_id: str) -> dict:
    supplier = suppliers.get(supplier_id)
    if not supplier:
        raise ValueError(data_invalid_supplier(supplier_id))
    return {"success": True, "data": supplier}
```

## 4. CAUTION Tool 实现

- [x] 4.1 实现 create_order（含限额检查、库存预留）

```python
from app.mock_erp import (
    orders, inventory, suppliers, order_counter,
    get_next_order_id, reserve_inventory, recalc_available
)
from app.errors import tool_limit, data_invalid_supplier, data_insufficient
from datetime import datetime

def create_order(type: str, items: list, customer: str = None,
                 supplier: str = None, address: str = None) -> dict:
    max_items = TOOL_LIMITS["create_order"]["max_items"]
    if len(items) > max_items:
        raise ValueError(tool_limit("create_order", max_items, len(items)))

    if type == "purchase" and supplier:
        if supplier not in suppliers:
            raise ValueError(data_invalid_supplier(supplier))

    if type == "sales":
        for item in items:
            sku = item["sku"]
            inv = inventory.get(sku)
            if inv and inv["available"] < item["qty"]:
                raise ValueError(data_insufficient(
                    inv["name"], inv["available"], item["qty"], inv["unit"]
                ))

    new_id = get_next_order_id()
    total = 0
    enriched_items = []
    for item in items:
        inv = inventory.get(item["sku"], {})
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
        "items": enriched_items,
        "total": total,
        "address": address if type == "sales" else None,
        "supplier": supplier if type == "purchase" else None,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
        "estimated_delivery": None,
        "cancel_reason": None,
        "notes": ""
    }
    orders[new_id] = new_order

    if type == "sales":
        for item in items:
            reserve_inventory(item["sku"], item["qty"])

    return {"success": True, "data": new_order}
```

## 5. DANGER Tool 实现

- [x] 5.1 实现 update_order（含状态校验）
- [x] 5.2 实现 cancel_order（含状态校验 + 库存释放）
- [x] 5.3 实现 delete_order（仅限 cancelled 状态）
- [x] 5.4 实现 adjust_inventory

```python
from app.mock_erp import can_mutate, release_inventory
from app.errors import data_not_found, data_conflict

def update_order(order_id: str, field: str, value: str) -> dict:
    order = orders.get(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    ok, msg = can_mutate(order_id, field)
    if not ok:
        raise ValueError(data_conflict("订单", order_id, msg))
    order[field] = value
    order["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    return {"success": True, "data": order}

def cancel_order(order_id: str, reason: str) -> dict:
    order = orders.get(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    ok, msg = can_transition(order_id, "cancelled")
    if not ok:
        raise ValueError(data_conflict("订单", order_id, msg))
    order["status"] = "cancelled"
    order["cancel_reason"] = reason
    order["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    if order["type"] == "sales":
        for item in order["items"]:
            release_inventory(item["sku"], item["qty"])
    return {"success": True, "data": order}

def delete_order(order_id: str) -> dict:
    order = orders.get(order_id)
    if not order:
        raise ValueError(data_not_found("订单", order_id))
    if order["status"] != "cancelled":
        raise ValueError(data_conflict("订单", order_id, "仅可删除已取消的订单"))
    del orders[order_id]
    return {"success": True, "data": {"deleted_order_id": order_id}}

def adjust_inventory(sku: str, delta: int, reason: str) -> dict:
    item = inventory.get(sku)
    if not item:
        raise ValueError(data_not_found("商品", sku))
    new_qty = item["qty"] + delta
    if new_qty < 0:
        raise ValueError(data_conflict("库存", sku, f"调整后数量不能为负数(当前{item['qty']}, 调整{delta})"))
    item["qty"] = new_qty
    recalc_available(sku)
    return {"success": True, "data": item}
```

## 6. Tool 注册表与执行器

- [x] 6.1 实现 TOOL_REGISTRY 映射
- [x] 6.2 实现 execute_tool 函数

```python
TOOL_REGISTRY = {
    "query_order": query_order,
    "query_orders": query_orders,
    "query_inventory": query_inventory,
    "query_supplier": query_supplier,
    "create_order": create_order,
    "update_order": update_order,
    "cancel_order": cancel_order,
    "delete_order": delete_order,
    "adjust_inventory": adjust_inventory,
}

def execute_tool(name: str, args: dict) -> dict:
    if name not in TOOL_REGISTRY:
        raise ValueError(tool_not_found(name))
    func = TOOL_REGISTRY[name]
    try:
        return func(**args)
    except ValueError as e:
        raise
    except TypeError as e:
        raise ValueError(tool_invalid_param(name, "", str(e)))
    except Exception as e:
        raise ValueError(sys_error(str(e)))
```
