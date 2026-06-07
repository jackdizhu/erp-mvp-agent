from pydantic import BaseModel
from typing import Optional


class ApprovalCreateRequest(BaseModel):
    """创建审批请求"""
    action_id: str
    tool: str
    args: dict
    session_id: Optional[str] = None


class ApprovalCreateResponse(BaseModel):
    """创建审批响应"""
    supported: bool
    action_id: str
    reason: Optional[str] = None
    fields: list = []
    irreversible: bool = False
    warning: Optional[str] = None


class ApprovalDecideRequest(BaseModel):
    """用户审批决定请求"""
    action_id: str
    approved: bool
    session_id: Optional[str] = None


class ApprovalDecideResponse(BaseModel):
    """用户审批决定响应"""
    user_op_id: str
    action_id: str
    approved: bool
    status: str  # "approved" | "rejected"