import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from erp_app.tools import TOOL_REGISTRY, TOOL_SCHEMAS
from erp_app.errors import tool_not_found, sys_error

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


def list_tools() -> List[Dict[str, Any]]:
    tools = []
    for schema in TOOL_SCHEMAS:
        tool_name = schema.get("name", "")
        support = TASK_SUPPORT_MAP.get(tool_name, "forbidden")
        tool = {
            "name": f"mcp_{tool_name}",
            "description": schema.get("description", ""),
            "inputSchema": schema.get("inputSchema", {}),
            "execution": {"taskSupport": support}
        }
        tools.append(tool)
    return tools


def get_task_support(tool_name: str) -> str:
    original_name = tool_name[4:] if tool_name.startswith("mcp_") else tool_name
    return TASK_SUPPORT_MAP.get(original_name, "forbidden")


def call_tool(name: str, arguments: dict) -> dict:
    original_name = name[4:] if name.startswith("mcp_") else name
    return execute_tool(original_name, arguments)