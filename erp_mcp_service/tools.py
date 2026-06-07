import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from erp_app.tools import TOOL_REGISTRY, TOOL_SCHEMAS
from erp_app.errors import tool_not_found, sys_error
from approval_manager import approval_manager
from approval_detail import get_approval_detail
from config import APPROVAL_TTL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASK_SUPPORT_MAP = {
    "query_order": "optional",
    "query_orders": "optional",
    "query_inventory": "optional",
    "query_supplier": "optional",
    "create_order": "optional",
    "update_order": "optional",
    "cancel_order": "optional",
    "delete_order": "optional",
    "adjust_inventory": "optional",
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


def _check_requires_approval(tool_name: str) -> bool:
    for schema in TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema.get("requiresApproval", False)
    return False


def _get_risk_level(tool_name: str) -> str:
    for schema in TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema.get("riskLevel", "SAFE")
    return "SAFE"


OPERATION_TITLES = {
    "update_order": "修改订单",
    "cancel_order": "取消订单",
    "delete_order": "删除订单",
    "adjust_inventory": "调整库存",
}


def _get_operation_title(tool_name: str) -> str:
    return OPERATION_TITLES.get(tool_name, tool_name)


def _handle_confirm_approval(arguments: dict) -> dict:
    action_id = arguments.get("action_id")
    approved = arguments.get("approved", False)

    if not action_id:
        return {
            "success": False,
            "error": "MISSING_ACTION_ID",
            "message": "缺少 action_id 参数"
        }

    action = approval_manager.get(action_id)
    if not action:
        return {
            "success": False,
            "error": "ACTION_NOT_FOUND",
            "message": f"审批动作 {action_id} 不存在或已过期"
        }

    if action.status != "pending":
        return {
            "success": False,
            "error": f"ACTION_ALREADY_{action.status.upper()}",
            "message": f"审批动作已是 {action.status} 状态"
        }

    if time.time() - action.created_at > action.ttl:
        action.status = "expired"
        return {
            "success": False,
            "error": "APPROVAL_EXPIRED",
            "message": "审批已过期，请重新发起操作"
        }

    if approved:
        success, error = approval_manager.confirm(action_id)
        if not success:
            return {
                "success": False,
                "error": error,
                "message": f"执行失败: {error}"
            }

        try:
            result = execute_tool(action.tool_name, action.arguments)
            return {
                "success": True,
                "action_id": action_id,
                "executed": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": "EXECUTION_FAILED",
                "message": f"执行失败: {str(e)}"
            }
    else:
        success, error = approval_manager.reject(action_id)
        return {
            "success": True,
            "action_id": action_id,
            "executed": False,
            "message": "操作已取消"
        }


def list_tools() -> List[Dict[str, Any]]:
    tools = []
    for schema in TOOL_SCHEMAS:
        tool_name = schema.get("name", "")
        support = TASK_SUPPORT_MAP.get(tool_name, "forbidden")
        tool = {
            "name": f"mcp_{tool_name}",
            "description": schema.get("description", ""),
            "inputSchema": schema.get("inputSchema", {}),
            "execution": {"taskSupport": support},
            "metadata": {
                "riskLevel": schema.get("riskLevel", "SAFE"),
                "requiresApproval": schema.get("requiresApproval", False),
                "irreversible": schema.get("irreversible", False),
                "approvalSummary": schema.get("approvalSummary", ""),
            }
        }
        tools.append(tool)

    tools.append({
        "name": "mcp_confirm_approval",
        "description": "确认或拒绝待审批的操作",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "审批动作ID (来自pending状态的action_id)"
                },
                "approved": {
                    "type": "boolean",
                    "description": "true=批准执行, false=拒绝并取消"
                }
            },
            "required": ["action_id", "approved"]
        },
        "metadata": {
            "riskLevel": "SAFE",
            "requiresApproval": False,
            "irreversible": False,
            "approvalSummary": ""
        }
    })

    return tools


def get_task_support(tool_name: str) -> str:
    original_name = tool_name[4:] if tool_name.startswith("mcp_") else tool_name
    return TASK_SUPPORT_MAP.get(original_name, "forbidden")


def call_tool(name: str, arguments: dict) -> dict:
    original_name = name[4:] if name.startswith("mcp_") else name

    if original_name == "confirm_approval":
        return _handle_confirm_approval(arguments)

    requires_approval = _check_requires_approval(original_name)

    if requires_approval:
        risk_level = _get_risk_level(original_name)

        try:
            approval_detail = get_approval_detail(original_name, arguments)
        except Exception:
            approval_detail = {
                "action_type": original_name,
                "fields": [],
                "changes": [],
                "irreversible": False
            }

        title = approval_detail.get("title") or _get_operation_title(original_name)
        summary = approval_detail.get("action_summary") or approval_detail.get("summary") or f"执行 {original_name}"
        description = approval_detail.get("description") or f"执行 {original_name} 操作"
        warning = approval_detail.get("warning")

        expires_at_ts = time.time() + APPROVAL_TTL

        try:
            action = approval_manager.create(
                tool_name=original_name,
                arguments=arguments,
                risk_level=risk_level,
                approval_detail=approval_detail,
                ttl=APPROVAL_TTL
            )
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "message": "待审批操作数量超限，请稍后重试"
            }

        return {
            "status": "PENDING",
            "action_id": action.action_id,
            "tool": original_name,
            "args": arguments,
            "risk_level": risk_level,
            "title": title,
            "summary": summary,
            "description": description,
            "warning": warning,
            "detail": approval_detail,
            "expires_at": expires_at_ts,
            "ttl_seconds": APPROVAL_TTL
        }

    return execute_tool(original_name, arguments)