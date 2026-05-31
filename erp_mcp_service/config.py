import os
from pathlib import Path
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".default.env")
load_dotenv(_project_root / ".local.env", override=True)

MCP_SERVICE_PORT = int(os.getenv("MCP_SERVICE_PORT", "9001"))
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
MCP_RESPONSE_MODE = os.getenv("MCP_RESPONSE_MODE", "auto")

ERP_BASE_PATH = _project_root / "erp_app"