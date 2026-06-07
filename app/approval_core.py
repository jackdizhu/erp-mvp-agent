import uuid
import time
from typing import Optional

from app.erp_client import erp_client
from app.config import APPROVAL_CONFIG
from app.approval_store import approval_store


OPERATION_TITLES = {
    "update_order": "修改订单",
    "cancel_order": "取消订单",
    "delete_order": "删除订单",
    "adjust_inventory": "调整库存",
}


def _get_operation_title(tool_name: str) -> str:
    return OPERATION_TITLES.get(tool_name, tool_name)


class ApprovalCore:
    def __init__(self):
        self.pending_actions: dict = {}
        self._ttl_seconds: int = APPROVAL_CONFIG["ttl_seconds"]
        self._max_pending: int = APPROVAL_CONFIG["max_pending"]

    def _generate_id(self) -> str:
        return f"act_{uuid.uuid4().hex[:8]}"

    def _is_expired(self, action: dict) -> bool:
        return time.time() > action["expires_at"]

    def create_pending(self, tool: str, args: dict, messages_context: list) -> Optional[dict]:
        self.cleanup_expired()

        if len(self.pending_actions) >= self._max_pending:
            return None

        action_id = self._generate_id()
        risk_level = erp_client.get_risk_level(tool)
        approval_info = erp_client.get_approval_detail(tool, args)

        title = approval_info.get("title") or _get_operation_title(tool)
        summary = approval_info.get("summary") or ""
        description = approval_info.get("description") or ""
        warning = approval_info.get("warning")
        detail = approval_info.get("detail", {})

        pending = {
            "status": "PENDING",
            "action_id": action_id,
            "tool": tool,
            "args": args,
            "messages_context": messages_context,
            "risk_level": risk_level,
            "title": title,
            "summary": summary,
            "description": description,
            "warning": warning,
            "detail": detail,
            "expires_at": time.time() + self._ttl_seconds,
            "ttl_seconds": self._ttl_seconds,
        }

        self.pending_actions[action_id] = pending

        # 同步注册到 approval_store 供两阶段审批使用
        approval_store.create(action_id, tool, args, detail)

        return pending

    def confirm(self, action_id: str, approved: bool, user_op_id: str = None) -> Optional[dict]:
        action = self.pending_actions.get(action_id)
        if not action:
            return None

        if self._is_expired(action):
            del self.pending_actions[action_id]
            return {"expired": True}

        if approved:
            result = action
            result["user_op_id"] = user_op_id
            del self.pending_actions[action_id]
            return {"approved": True, "action": result}
        else:
            result = action
            result["user_op_id"] = user_op_id
            del self.pending_actions[action_id]
            return {"approved": False, "action": result}

    def cleanup_expired(self) -> int:
        expired_ids = [
            aid for aid, action in self.pending_actions.items()
            if self._is_expired(action)
        ]
        for aid in expired_ids:
            del self.pending_actions[aid]
        return len(expired_ids)


approval_core = ApprovalCore()