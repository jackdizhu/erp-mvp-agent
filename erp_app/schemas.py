from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ApprovalChange(BaseModel):
    field: str
    label: str
    old: str
    new: str


class ApprovalDetail(BaseModel):
    action_type: str
    fields: list[Dict[str, str]]
    changes: list[ApprovalChange]
    irreversible: bool


class PendingActionSchema(BaseModel):
    status: str = "PENDING"
    action_id: str
    tool: str
    args: Dict[str, Any]
    risk_level: str
    title: str
    summary: str
    description: str
    warning: Optional[str] = None
    detail: ApprovalDetail
    expires_at: float
    ttl_seconds: int


REQUIRED_FIELDS = [
    "status", "action_id", "tool", "args", "risk_level",
    "title", "summary", "description", "warning", "detail",
    "expires_at", "ttl_seconds"
]

RISK_LEVELS = ("SAFE", "WARNING", "DANGER")


def validate_pending_action(data: dict) -> tuple[bool, Optional[str]]:
    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Missing required field: {field}"

    if data["status"] != "PENDING":
        return False, f"Invalid status: {data['status']}, must be 'PENDING'"

    if not data["action_id"].startswith("act_"):
        return False, f"Invalid action_id format: {data['action_id']}, must start with 'act_'"

    if data["risk_level"] not in RISK_LEVELS:
        return False, f"Invalid risk_level: {data['risk_level']}, must be one of {RISK_LEVELS}"

    if not isinstance(data["expires_at"], (int, float)):
        return False, f"expires_at must be numeric, got {type(data['expires_at']).__name__}"

    if not isinstance(data["ttl_seconds"], int):
        return False, f"ttl_seconds must be integer, got {type(data['ttl_seconds']).__name__}"

    return True, None