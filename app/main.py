from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import queue
import re
import threading
import uuid
import logging
import requests
from pathlib import Path

import yaml

from app.agent import chat, confirm_action, stream_chat, format_sse_event, _current_on_event
from app.agent_logger import SessionLogger
from app.clients.client_factory import register_erp_adapter, client_factory
from app.clients.mcp_registry import reload_registry, init_registry
from app.config import CLIENT_BACKEND, ENABLE_LOCAL_ADAPTER, MCP_SERVICE_URL, ENABLE_SKILL
from app.models import (
    ApprovalCreateRequest, ApprovalCreateResponse,
    ApprovalDecideRequest, ApprovalDecideResponse
)
from app.approval_store import approval_store
from app.skills.registry import get_skill_registry, init_skill_registry
from app.skills.validator import SkillValidator
from app.skills.loader import SkillConfig
from erp_app.main import router as erp_router
from erp_app.db import init_db as init_erp_db
from erp_app.seed import seed_data

app = FastAPI(title="ERP Agent MVP")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(erp_router)


@app.get("/health")
async def health_check():
    registry = get_skill_registry()
    return {
        "status": "healthy",
        "service": "erp-agent-backend",
        "client_backend": CLIENT_BACKEND,
        "enable_local_adapter": ENABLE_LOCAL_ADAPTER,
        "enable_skill": ENABLE_SKILL,
        "skill_count": len(registry.get_all_skills()) if registry else 0,
    }


def check_mcp_service_ready(url: str, timeout: float = 5.0) -> bool:
    health_url = f"{url.rstrip('/')}/health"
    try:
        resp = requests.get(health_url, timeout=timeout)
        if resp.status_code == 200:
            logger.info(f"MCP Service health check passed at {health_url}")
            return True
        else:
            logger.error(f"MCP Service at {health_url} returned {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"MCP Service at {health_url} is not reachable (ConnectionError)")
        logger.error(f"Please ensure the MCP service is started on {url}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"MCP Service at {health_url} health check timed out after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"MCP Service health check failed at {health_url}: {type(e).__name__}: {e}")
        return False


@app.on_event("startup")
def on_startup():
    init_erp_db()
    seed_data()
    if CLIENT_BACKEND in ["mcp", "hybrid"]:
        if MCP_SERVICE_URL:
            logger.info(f"CLIENT_BACKEND={CLIENT_BACKEND}, will check MCP Service at {MCP_SERVICE_URL}")
            if not check_mcp_service_ready(MCP_SERVICE_URL):
                logger.warning(f"MCP Service is not ready at {MCP_SERVICE_URL}, proceeding with registry init.")
        init_registry()
    if ENABLE_LOCAL_ADAPTER:
        register_erp_adapter()
    # Initialize Skill framework (after client_factory is ready)
    try:
        init_skill_registry()
        registry = get_skill_registry()
        count = len(registry.get_all_skills()) if registry else 0
        logger.info(f"Skill registry initialized with {count} skills")
    except Exception as e:
        logger.error(f"Failed to initialize skill registry: {e}")


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []
    session_id: Optional[str] = None


class ConfirmRequest(BaseModel):
    action_id: str
    approved: bool
    history: list[HistoryMessage] = []
    session_id: Optional[str] = None
    user_op_id: Optional[str] = None


class ToolCallResult(BaseModel):
    tool: str
    args: dict
    result: Optional[dict] = None
    error: Optional[dict] = None
    status: Optional[str] = None
    action_id: Optional[str] = None


class PendingAction(BaseModel):
    status: str = "PENDING"
    action_id: str
    tool: str
    args: dict
    risk_level: str
    title: str
    summary: str
    description: str
    warning: Optional[str] = None
    detail: dict
    expires_at: float
    ttl_seconds: int


class ErrorInfo(BaseModel):
    code: str
    recoverable: bool


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallResult] = []
    pending_action: Optional[PendingAction] = None
    error: Optional[ErrorInfo] = None


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    history = [h.model_dump() for h in req.history]
    session_id = req.session_id if req.session_id else f"none_{uuid.uuid4().hex[:8]}"

    logger = SessionLogger(session_id)

    # For /chat (sync), no SSE stream; pass None on_event. Skill observability
    # still writes log entries via logger.
    result = chat(req.message, history, logger)
    return ChatResponse(**result)


@app.post("/chat/confirm", response_model=ChatResponse)
async def confirm_endpoint(req: ConfirmRequest):
    history = [h.model_dump() for h in req.history]
    session_id = req.session_id if req.session_id else f"none_{uuid.uuid4().hex[:8]}"

    logger = SessionLogger(session_id)

    result = confirm_action(req.action_id, req.approved, history, req.user_op_id, logger)
    return ChatResponse(**result)


@app.post("/chat/stream")
async def stream_endpoint(req: ChatRequest):
    history = [h.model_dump() for h in req.history]
    session_id = req.session_id if req.session_id else f"none_{uuid.uuid4().hex[:8]}"

    logger = SessionLogger(session_id)

    q = queue.Queue()

    def on_event(event_type: str, data: dict):
        formatted = format_sse_event(event_type, data)
        q.put(formatted)

    def run_sync():
        try:
            # Inject on_event into agent context (decision D1: contextvars)
            token = _current_on_event.set(on_event)
            try:
                stream_chat(req.message, history, on_event, logger)
            finally:
                _current_on_event.reset(token)
        except Exception as e:
            error_data = {"message": str(e), "code": "stream_error"}
            logger.log_error(
                "stream_error",
                f"Stream error for session {session_id}: {type(e).__name__}: {str(e)}"
            )
            q.put(format_sse_event("done", {
                "complete": False,
                "tool_calls": [],
                "pending_action": None,
                "error": error_data
            }))
        finally:
            q.put(None)

    thread = threading.Thread(target=run_sync, daemon=True)
    thread.start()

    async def event_generator():
        while True:
            try:
                item = q.get(timeout=1)
                if item is None:
                    break
                yield item
            except queue.Empty:
                if not thread.is_alive():
                    break
                yield ":\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


class ReloadResponse(BaseModel):
    added: int
    removed: int
    updated: int
    failed: int


@app.post("/api/mcp/reload", response_model=ReloadResponse)
async def mcp_reload():
    result = reload_registry()
    return ReloadResponse(**result)


@app.get("/api/mcp/debug")
async def mcp_debug():
    from app.clients.mcp_registry import get_registry, _registry
    registry = get_registry()
    return {
        "registry_exists": registry is not None,
        "client_count": len(registry._clients) if registry else 0,
        "clients": list(registry._clients.keys()) if registry else [],
        "client_backend": CLIENT_BACKEND,
        "enable_local_adapter": ENABLE_LOCAL_ADAPTER,
        "mcp_service_url": MCP_SERVICE_URL
    }


@app.post("/api/approval/create", response_model=ApprovalCreateResponse)
async def approval_create(req: ApprovalCreateRequest):
    """前端收到审批信息后，创建审批记录并验证"""
    supported, reason = approval_store.validate(req.action_id)
    if not supported:
        return ApprovalCreateResponse(
            supported=False,
            action_id=req.action_id,
            reason=reason
        )

    record = approval_store.get(req.action_id)
    detail = record.detail if record else {}
    return ApprovalCreateResponse(
        supported=True,
        action_id=req.action_id,
        fields=detail.get("fields", []),
        irreversible=detail.get("irreversible", False),
        warning=detail.get("warning")
    )


@app.post("/api/approval/decide", response_model=ApprovalDecideResponse)
async def approval_decide(req: ApprovalDecideRequest):
    """用户点击同意/不同意，创建用户审批操作ID"""
    success, user_op_id, error = approval_store.decide(req.action_id, req.approved)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return ApprovalDecideResponse(
        user_op_id=user_op_id,
        action_id=req.action_id,
        approved=req.approved,
        status="approved" if req.approved else "rejected"
    )


def _safe_get_all_tool_names() -> list:
    """Get available tool names from client_factory, gracefully degrading if MCP is down.

    The MCP client raises HTTPError when its service is unreachable. We catch
    and return whatever tools are currently registered (may be empty if all
    backends failed at startup).
    """
    try:
        return [t["function"]["name"] for t in client_factory.get_all_tools()]
    except Exception as e:
        logger.warning(f"Failed to enumerate tools from client_factory: {e}")
        # Fall back to erp_local tool names from TOOL_SCHEMAS
        try:
            from erp_app.tools import TOOL_SCHEMAS
            return [t.get("name", "") for t in TOOL_SCHEMAS if t.get("name")]
        except Exception:
            return []


# --- Skill management API endpoints (spec: skill-api) ---

class SkillLoadRequest(BaseModel):
    skill_name: str


class SkillValidateRequest(BaseModel):
    skill_name: str
    skill_data: dict


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    intent_patterns: dict
    prompt_fragment: str = ""
    tools: list = []
    workflow: Optional[dict] = None


@app.get("/api/skills/available")
async def skills_available():
    """List all registered skills (preset + custom)."""
    registry = get_skill_registry()
    if not registry:
        return []
    return [
        {
            "name": name,
            "description": config.description,
            "category": config.category,
            "tools": config.tools,
            "has_workflow": config.workflow is not None,
            "has_handler": config.has_handler(),
        }
        for name, config in registry.get_all_skills().items()
    ]


@app.get("/api/skills/loaded")
async def skills_loaded():
    """List currently loaded skills. Phase 1/2: same as available."""
    registry = get_skill_registry()
    if not registry:
        return []
    return [
        {"name": name, "description": config.description, "category": config.category}
        for name, config in registry.get_all_skills().items()
    ]


@app.post("/api/skills/load")
async def skill_load(req: SkillLoadRequest):
    """Load a skill on demand (reserved for future session-scoped skills)."""
    registry = get_skill_registry()
    if not registry:
        raise HTTPException(status_code=500, detail="Skill registry not initialized")
    skill = registry.get_skill(req.skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{req.skill_name}' not found")
    return {
        "success": True,
        "name": skill.name,
        "tools": skill.tools,
        "has_workflow": skill.workflow is not None,
        "has_handler": skill.has_handler(),
    }


@app.post("/api/skills/validate")
async def skill_validate(req: SkillValidateRequest):
    """Validate a custom skill configuration."""
    validator = SkillValidator()
    # client_factory.get_all_tools() returns OpenAI-format dicts; name field is
    # already the short form (alias mapping strips mcp_ prefix at registration).
    available_tools = _safe_get_all_tool_names()
    is_valid, errors = validator.validate_config(
        req.skill_data, available_tools, is_custom=True
    )
    return {"valid": is_valid, "errors": errors}


@app.post("/api/skills/create")
async def skill_create(req: SkillCreateRequest):
    """Create a custom skill. Writes skill.yaml to skills_custom/ and hot-loads."""
    # 1. Name format check
    if not re.match(r'^[a-zA-Z0-9_-]+$', req.name):
        raise HTTPException(
            status_code=400,
            detail="Skill 名称只允许字母、数字、下划线和连字符",
        )

    registry = get_skill_registry()

    # 2. Name collision check
    if registry and registry.get_skill(req.name):
        raise HTTPException(
            status_code=400, detail=f"Skill '{req.name}' 已存在"
        )

    # 3. Build config + validate
    config_data = {
        "name": req.name,
        "version": "1.0",
        "description": req.description,
        "category": "custom",
        "intent_patterns": req.intent_patterns,
        "tools": req.tools,
        "prompt_fragment": req.prompt_fragment,
        "workflow": req.workflow,
    }
    validator = SkillValidator()
    available_tools = _safe_get_all_tool_names()
    is_valid, errors = validator.validate_config(
        config_data, available_tools, is_custom=True
    )
    if not is_valid:
        raise HTTPException(
            status_code=400, detail="; ".join(errors)
        )

    # 4. Write to disk (skills_custom/ flat — decision D4)
    skill_dir = Path(__file__).resolve().parents[1].parent / "skills_custom" / req.name
    skill_dir.mkdir(parents=True, exist_ok=True)
    with open(skill_dir / "skill.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

    # 5. Hot-load into registry
    if registry:
        config = SkillConfig(name=req.name, config_path=skill_dir)
        if config.load():
            registry.add_skill(config)

    return {"success": True, "name": req.name}


BACKEND_PORT = int(os.getenv("BACKEND_PORT", "9000"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)