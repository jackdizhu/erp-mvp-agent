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

SSE_CONFIG = {
    "ping_interval": int(os.getenv("SSE_PING_INTERVAL", "15")),
    "timeout_seconds": int(os.getenv("SSE_TIMEOUT", "60")),
    "max_chunk_size": int(os.getenv("SSE_MAX_CHUNK", "500")),
}
