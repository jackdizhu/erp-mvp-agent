from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from erp_app.tools import TOOL_SCHEMAS, execute_tool
from erp_app.approval_detail import generate_approval_detail
from erp_app.config import ACTION_SUMMARIES

router = APIRouter(prefix="/erp", tags=["erp"])


class ToolExecuteRequest(BaseModel):
    name: str
    args: dict


class ApprovalDetailRequest(BaseModel):
    tool_name: str
    args: dict


@router.get("/tools/schemas")
async def get_tool_schemas():
    return {"schemas": TOOL_SCHEMAS}


@router.post("/tools/execute")
async def execute_tool_endpoint(req: ToolExecuteRequest):
    try:
        result = execute_tool(req.name, req.args)
        return result
    except ValueError as e:
        err = e.args[0] if e.args else {"code": "UNKNOWN", "message": str(e)}
        return {"success": False, "error": err.to_dict() if hasattr(err, "to_dict") else {"message": str(e)}}


@router.post("/approval/detail")
async def get_approval_detail(req: ApprovalDetailRequest):
    detail = generate_approval_detail(req.tool_name, req.args)
    summary_template = ACTION_SUMMARIES.get(req.tool_name, "执行{tool}")
    try:
        summary = summary_template.format(**req.args, tool=req.tool_name)
    except KeyError:
        summary = summary_template
    return {
        "summary": summary,
        "detail": detail
    }
