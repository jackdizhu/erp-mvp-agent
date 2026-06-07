from erp_app.config import TOOL_LIMITS
from erp_app.errors import tool_not_found, tool_limit, sys_error
from erp_app.services.order_service import (
    create_order_service, update_order_service, cancel_order_service,
    delete_order_service
)
from erp_app.services.inventory_service import adjust_inventory_service
from erp_app.db import query_order, query_orders_batch, query_inventory, query_supplier

TOOL_SCHEMAS = [
    {
        "name": "query_order",
        "description": "根据订单ID查询订单详情",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "订单编号"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "query_orders",
        "description": "批量查询多个订单的状态",
        "inputSchema": {
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
    },
    {
        "name": "query_inventory",
        "description": "根据商品SKU查询库存信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "商品SKU编号"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "query_supplier",
        "description": "根据供应商ID查询供应商信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_id": {
                    "type": "string",
                    "description": "供应商编号"
                }
            },
            "required": ["supplier_id"]
        }
    },
    {
        "name": "create_order",
        "description": "创建销售订单或采购订单",
        "inputSchema": {
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
    },
    {
        "name": "update_order",
        "description": "修改订单的指定字段",
        "riskLevel": "DANGER",
        "requiresApproval": True,
        "irreversible": False,
        "approvalSummary": "修改订单{order_id}的{field}",
        "inputSchema": {
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
    },
    {
        "name": "cancel_order",
        "description": "取消订单并释放预留库存",
        "riskLevel": "DANGER",
        "requiresApproval": True,
        "irreversible": False,
        "approvalSummary": "取消订单{order_id}",
        "inputSchema": {
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
    },
    {
        "name": "delete_order",
        "description": "删除已取消的订单(仅限cancelled状态)",
        "riskLevel": "DANGER",
        "requiresApproval": True,
        "irreversible": True,
        "approvalSummary": "删除订单{order_id}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "订单编号"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "adjust_inventory",
        "description": "调整商品库存数量(正数入库/负数出库)",
        "riskLevel": "DANGER",
        "requiresApproval": True,
        "irreversible": False,
        "approvalSummary": "调整{sku}库存{delta}",
        "inputSchema": {
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
]


def _tool_query_order(order_id: str) -> dict:
    order = query_order(order_id)
    if not order:
        from erp_app.errors import data_not_found
        raise ValueError(data_not_found("订单", order_id))
    return {"success": True, "data": order}


def _tool_query_orders(order_ids: list) -> dict:
    max_batch = TOOL_LIMITS["query_orders"]["max_batch"]
    if len(order_ids) > max_batch:
        raise ValueError(tool_limit("query_orders", max_batch, len(order_ids)))
    results = query_orders_batch(order_ids)
    return {"success": True, "data": results}


def _tool_query_inventory(sku: str) -> dict:
    item = query_inventory(sku)
    if not item:
        from erp_app.errors import data_not_found
        raise ValueError(data_not_found("商品", sku))
    return {"success": True, "data": item}


def _tool_query_supplier(supplier_id: str) -> dict:
    from erp_app.db import query_supplier as db_q
    supplier = db_q(supplier_id)
    if not supplier:
        from erp_app.errors import data_invalid_supplier
        raise ValueError(data_invalid_supplier(supplier_id))
    return {"success": True, "data": supplier}


def _tool_create_order(type: str, items: list, customer: str = None,
                       supplier: str = None, address: str = None) -> dict:
    max_items = TOOL_LIMITS["create_order"]["max_items"]
    if len(items) > max_items:
        raise ValueError(tool_limit("create_order", max_items, len(items)))
    return create_order_service(type, items, customer, supplier, address)


def _tool_update_order(order_id: str, field: str, value: str) -> dict:
    return update_order_service(order_id, field, value)


def _tool_cancel_order(order_id: str, reason: str) -> dict:
    return cancel_order_service(order_id, reason)


def _tool_delete_order(order_id: str) -> dict:
    return delete_order_service(order_id)


def _tool_adjust_inventory(sku: str, delta: int, reason: str) -> dict:
    return adjust_inventory_service(sku, delta, reason)


TOOL_REGISTRY = {
    "query_order": _tool_query_order,
    "query_orders": _tool_query_orders,
    "query_inventory": _tool_query_inventory,
    "query_supplier": _tool_query_supplier,
    "create_order": _tool_create_order,
    "update_order": _tool_update_order,
    "cancel_order": _tool_cancel_order,
    "delete_order": _tool_delete_order,
    "adjust_inventory": _tool_adjust_inventory,
}


def execute_tool(name: str, args: dict) -> dict:
    if name not in TOOL_REGISTRY:
        raise ValueError(tool_not_found(name))
    func = TOOL_REGISTRY[name]
    try:
        return func(**args)
    except ValueError:
        raise
    except TypeError as e:
        raise ValueError(sys_error(str(e)))
    except Exception as e:
        raise ValueError(sys_error(str(e)))
