from erp_app.tools import TOOL_SCHEMAS, TOOL_REGISTRY, execute_tool as erp_execute_tool
from erp_app.config import TOOL_RISK_LEVELS, ACTION_SUMMARIES
from erp_app.approval_detail import generate_approval_detail


OPERATION_TITLES = {
    "update_order": "修改订单",
    "cancel_order": "取消订单",
    "delete_order": "删除订单",
    "adjust_inventory": "调整库存",
}


def _get_operation_title(tool_name: str) -> str:
    return OPERATION_TITLES.get(tool_name, tool_name)


class ErpClient:
    def get_tools(self) -> list:
        return TOOL_SCHEMAS

    def get_risk_level(self, tool_name: str) -> str:
        return TOOL_RISK_LEVELS.get(tool_name, "SAFE")

    def execute_tool(self, name: str, args: dict) -> dict:
        return erp_execute_tool(name, args)

    def get_approval_detail(self, tool_name: str, args: dict) -> dict:
        summary_template = ACTION_SUMMARIES.get(tool_name, "执行{tool}")
        try:
            summary = summary_template.format(**args, tool=tool_name)
        except KeyError:
            summary = summary_template

        detail = generate_approval_detail(tool_name, args)

        return {
            "title": detail.get("title") or _get_operation_title(tool_name),
            "summary": summary,
            "description": detail.get("description") or "",
            "warning": detail.get("warning"),
            "detail": {
                "action_type": detail.get("action_type", tool_name),
                "fields": detail.get("fields", []),
                "changes": detail.get("changes", []),
                "irreversible": detail.get("irreversible", False)
            }
        }


erp_client = ErpClient()