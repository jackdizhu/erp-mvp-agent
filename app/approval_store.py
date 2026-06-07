import uuid
import time
from typing import Optional


class ApprovalRecord:
    def __init__(self, action_id: str, tool: str, args: dict, detail: dict):
        self.action_id = action_id
        self.tool = tool
        self.args = args
        self.detail = detail
        self.supported = True
        self.reason = None
        self.user_op_id = None
        self.approved = None
        self.created_at = time.time()
        self.decided_at = None

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "tool": self.tool,
            "args": self.args,
            "detail": self.detail,
            "supported": self.supported,
            "reason": self.reason,
            "user_op_id": self.user_op_id,
            "approved": self.approved,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }


class ApprovalStore:
    """审批记录持久化存储，替代 approval_core 的 pending_actions dict"""

    def __init__(self):
        self._records: dict[str, ApprovalRecord] = {}
        self._ttl_seconds: int = 300
        self._max_pending: int = 10

    def create(self, action_id: str, tool: str, args: dict, detail: dict) -> ApprovalRecord:
        self._cleanup_expired()
        if len(self._records) >= self._max_pending:
            raise ValueError("MAX_PENDING_EXCEEDED")
        record = ApprovalRecord(action_id, tool, args, detail)
        self._records[action_id] = record
        return record

    def validate(self, action_id: str) -> tuple[bool, Optional[str]]:
        """验证审批是否支持"""
        record = self._records.get(action_id)
        if not record:
            return False, "ACTION_NOT_FOUND"
        if record.decided_at:
            return False, "ALREADY_DECIDED"
        return True, None

    def mark_unsupported(self, action_id: str, reason: str):
        record = self._records.get(action_id)
        if record:
            record.supported = False
            record.reason = reason

    def decide(self, action_id: str, approved: bool) -> tuple[bool, Optional[str], Optional[str]]:
        """用户审批决定，返回 (success, user_op_id, error)"""
        record = self._records.get(action_id)
        if not record:
            return False, None, "ACTION_NOT_FOUND"
        if not record.supported:
            return False, None, "NOT_SUPPORTED"
        if record.user_op_id:
            return False, None, "ALREADY_DECIDED"
        user_op_id = f"uop_{uuid.uuid4().hex[:12]}"
        record.user_op_id = user_op_id
        record.approved = approved
        record.decided_at = time.time()
        return True, user_op_id, None

    def get(self, action_id: str) -> Optional[ApprovalRecord]:
        return self._records.get(action_id)

    def _cleanup_expired(self):
        expired = [
            aid for aid, rec in self._records.items()
            if time.time() - rec.created_at > self._ttl_seconds and not rec.decided_at
        ]
        for aid in expired:
            del self._records[aid]


approval_store = ApprovalStore()