from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid
import time
from threading import Lock


@dataclass
class PendingAction:
    action_id: str
    tool_name: str
    arguments: dict
    risk_level: str
    approval_detail: dict
    created_at: float
    ttl: int
    status: str = "pending"


class ApprovalManager:
    def __init__(self, default_ttl: int = 300, max_pending: int = 10):
        self._pending: Dict[str, PendingAction] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self.max_pending = max_pending

    def create(self, tool_name: str, arguments: dict,
               risk_level: str, approval_detail: dict,
               ttl: int = None) -> PendingAction:
        with self._lock:
            self._cleanup_expired()
            if len(self._pending) >= self.max_pending:
                raise ValueError("MAX_PENDING_EXCEEDED")

            action = PendingAction(
                action_id=f"act_{uuid.uuid4().hex[:12]}",
                tool_name=tool_name,
                arguments=arguments,
                risk_level=risk_level,
                approval_detail=approval_detail,
                created_at=time.time(),
                ttl=ttl or self.default_ttl
            )
            self._pending[action.action_id] = action
            return action

    def confirm(self, action_id: str) -> tuple[bool, Any]:
        with self._lock:
            action = self._pending.get(action_id)
            if not action:
                return False, "ACTION_NOT_FOUND"
            if action.status != "pending":
                return False, f"ACTION_ALREADY_{action.status.upper()}"
            if self._is_expired(action):
                action.status = "expired"
                return False, "APPROVAL_EXPIRED"

            action.status = "approved"
            return True, None

    def reject(self, action_id: str) -> tuple[bool, str]:
        with self._lock:
            action = self._pending.get(action_id)
            if not action:
                return False, "ACTION_NOT_FOUND"
            if action.status != "pending":
                return False, f"ACTION_ALREADY_{action.status.upper()}"

            action.status = "rejected"
            return True, None

    def get(self, action_id: str) -> Optional[PendingAction]:
        return self._pending.get(action_id)

    def _is_expired(self, action: PendingAction) -> bool:
        return (time.time() - action.created_at) > action.ttl

    def _cleanup_expired(self):
        expired = [
            aid for aid, action in self._pending.items()
            if action.status == "pending" and self._is_expired(action)
        ]
        for aid in expired:
            self._pending[aid].status = "expired"

    def cleanup(self):
        with self._lock:
            self._cleanup_expired()


approval_manager = ApprovalManager()