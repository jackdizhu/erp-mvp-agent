import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from erp_app.approval_detail import generate_approval_detail


def get_approval_detail(tool_name: str, args: dict) -> dict:
    return generate_approval_detail(tool_name, args)