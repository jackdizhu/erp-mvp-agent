from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import queue
import threading
import uuid

from app.agent import chat, confirm_action, stream_chat, format_sse_event
from app.agent_logger import SessionLogger
from erp_app.main import router as erp_router
from erp_app.db import init_db as init_erp_db
from erp_app.seed import seed_data

app = FastAPI(title="ERP Agent MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(erp_router)


@app.on_event("startup")
def on_startup():
    init_erp_db()
    seed_data()


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


class ToolCallResult(BaseModel):
    tool: str
    args: dict
    result: Optional[dict] = None
    error: Optional[dict] = None
    status: Optional[str] = None
    action_id: Optional[str] = None


class PendingAction(BaseModel):
    id: str
    tool: str
    args: dict
    risk_level: str
    summary: str
    detail: dict


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

    result = chat(req.message, history, logger)
    return ChatResponse(**result)


@app.post("/chat/confirm", response_model=ChatResponse)
async def confirm_endpoint(req: ConfirmRequest):
    history = [h.model_dump() for h in req.history]
    session_id = req.session_id if req.session_id else f"none_{uuid.uuid4().hex[:8]}"

    logger = SessionLogger(session_id)

    result = confirm_action(req.action_id, req.approved, history, logger)
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
            stream_chat(req.message, history, on_event, logger)
        except Exception as e:
            error_data = {"message": str(e), "code": "stream_error"}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)