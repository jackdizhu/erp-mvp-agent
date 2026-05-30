import uuid
import time
from typing import Optional

from app.config import APPROVAL_CONFIG, ACTION_SUMMARIES, TOOL_RISK_LEVELS
from app.mock_erp import orders, inventory


class ApprovalManager:
    def __init__(self):
        self.pending_actions: dict = {}

    def _generate_id(self) -> str:
        return f"act_{uuid.uuid4().hex[:8]}"

    def _is_expired(self, action: dict) -> bool:
        return time.time() > action["expires_at"]

    def get_risk_level(self, tool_name: str) -> str:
        return TOOL_RISK_LEVELS.get(tool_name, "SAFE")

    def create_pending(self, tool: str, args: dict,
                       messages_context: list) -> Optional[dict]:
        self.cleanup_expired()

        if len(self.pending_actions) >= APPROVAL_CONFIG["max_pending"]:
            return None

        action_id = self._generate_id()
        ttl = APPROVAL_CONFIG["ttl_seconds"]

        pending = {
            "id": action_id,
            "tool": tool,
            "args": args,
            "messages_context": messages_context,
            "risk_level": self.get_risk_level(tool),
            "summary": self.generate_summary(tool, args),
            "detail": self.generate_detail(tool, args),
            "created_at": time.time(),
            "expires_at": time.time() + ttl,
        }

        self.pending_actions[action_id] = pending
        return pending

    def confirm(self, action_id: str, approved: bool) -> Optional[dict]:
        action = self.pending_actions.get(action_id)
        if not action:
            return None

        if self._is_expired(action):
            del self.pending_actions[action_id]
            return {"expired": True}

        if approved:
            result = action
            del self.pending_actions[action_id]
            return {"approved": True, "action": result}
        else:
            del self.pending_actions[action_id]
            return {"approved": False}

    def cleanup_expired(self) -> int:
        expired_ids = [
            aid for aid, action in self.pending_actions.items()
            if self._is_expired(action)
        ]
        for aid in expired_ids:
            del self.pending_actions[aid]
        return len(expired_ids)

    def generate_summary(self, tool_name: str, args: dict) -> str:
        template = ACTION_SUMMARIES.get(tool_name, "执行{tool}")
        try:
            return template.format(**args, tool=tool_name)
        except KeyError:
            return template

    def generate_detail(self, tool_name: str, args: dict) -> dict:
        fields = []
        irreversible = False

        if tool_name == "update_order":
            order = orders.get(args.get("order_id", ""))
            fields = [
                {"name": "操作类型", "value": "修改订单"},
                {"name": "订单编号", "value": args.get("order_id", "")},
                {"name": "修改字段", "value": args.get("field", "")},
                {"name": "原值", "value": str(order.get(args.get("field", ""), "")) if order else "未知"},
                {"name": "新值", "value": args.get("value", "")},
            ]
        elif tool_name == "cancel_order":
            order = orders.get(args.get("order_id", ""))
            fields = [
                {"name": "操作类型", "value": "取消订单"},
                {"name": "订单编号", "value": args.get("order_id", "")},
                {"name": "当前状态", "value": order.get("status", "") if order else "未知"},
                {"name": "取消原因", "value": args.get("reason", "")},
            ]
        elif tool_name == "delete_order":
            order = orders.get(args.get("order_id", ""))
            fields = [
                {"name": "操作类型", "value": "删除订单"},
                {"name": "订单编号", "value": args.get("order_id", "")},
                {"name": "当前状态", "value": order.get("status", "") if order else "未知"},
            ]
            irreversible = True
        elif tool_name == "adjust_inventory":
            item = inventory.get(args.get("sku", ""))
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


approval_manager = ApprovalManager()
