from typing import List, Dict, Any
from erp_app.tools import TOOL_SCHEMAS


def to_openai_format(mcp_tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "parameters": mcp_tool.get("inputSchema", {})
        }
    }


def get_openai_tools() -> List[Dict[str, Any]]:
    return [to_openai_format(t) for t in TOOL_SCHEMAS]