from pathlib import Path
import os

from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".default.env")
load_dotenv(_project_root / ".local.env", override=True)

APPROVAL_CONFIG = {
    "ttl_seconds": int(os.getenv("APPROVAL_TTL", "300")),
    "max_pending": int(os.getenv("APPROVAL_MAX_PENDING", "10")),
}

HISTORY_WINDOW = {
    "default_n": int(os.getenv("HISTORY_WINDOW_N", "6")),
}

SSE_CONFIG = {
    "ping_interval": int(os.getenv("SSE_PING_INTERVAL", "15")),
    "timeout_seconds": int(os.getenv("SSE_TIMEOUT", "60")),
    "max_chunk_size": int(os.getenv("SSE_MAX_CHUNK", "500")),
}

TIMEOUT_CONFIG = {
    "llm_call": int(os.getenv("LLM_TIMEOUT", "15")),
    "mcp_request": int(os.getenv("MCP_REQUEST_TIMEOUT", "10")),
    "mcp_connect": int(os.getenv("MCP_CONNECT_TIMEOUT", "5")),
}

CLIENT_BACKEND = os.getenv("CLIENT_BACKEND", "hybrid")

ENABLE_LOCAL_ADAPTER = os.getenv("ENABLE_LOCAL_ADAPTER", "true").lower() in ("true", "1", "yes")

MCP_SERVICE_URL = os.getenv("MCP_SERVICE_URL", "")

# Skill framework (decision D4)
# Phase 1: default False (backward compatible)
# Phase 2: default True (skill matching active)
ENABLE_SKILL = os.getenv("ENABLE_SKILL", "false").lower() in ("true", "1", "yes")
