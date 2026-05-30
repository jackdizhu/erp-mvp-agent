# Chat API — Tasks

> Spec: [specs/chat-api/spec.md](spec.md)
> File: `/app/main.py`

---

## 1. Pydantic 请求/响应模型

- [x] 1.1 实现 ChatRequest 模型
- [x] 1.2 实现 ConfirmRequest 模型
- [x] 1.3 实现 ChatResponse 模型

```python
from pydantic import BaseModel
from typing import Optional

class HistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []

class ConfirmRequest(BaseModel):
    action_id: str
    approved: bool
    history: list[HistoryMessage] = []

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
```

## 2. FastAPI 应用与路由

- [x] 2.1 实现 FastAPI 应用初始化与 CORS 中间件
- [x] 2.2 实现 POST /chat 端点
- [x] 2.3 实现 POST /chat/confirm 端点

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.agent import chat, confirm_action

app = FastAPI(title="ERP Agent MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    history = [h.model_dump() for h in req.history]
    result = chat(req.message, history)
    return ChatResponse(**result)

@app.post("/chat/confirm", response_model=ChatResponse)
async def confirm_endpoint(req: ConfirmRequest):
    history = [h.model_dump() for h in req.history]
    result = confirm_action(req.action_id, req.approved, history)
    return ChatResponse(**result)
```

## 3. 启动入口

- [x] 3.1 实现 uvicorn 启动配置

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```
