from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import uuid
import sys
import time
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MCP_SERVICE_PORT, MCP_API_KEY, MCP_RESPONSE_MODE
from tools import list_tools, call_tool, get_task_support
from task_manager import task_manager
from session_manager import session_manager
from approval_manager import approval_manager
from erp_app.db import init_db as init_erp_db
from erp_app.seed import seed_data

app = FastAPI(title="ERP MCP Service")

PROTOCOL_VERSION = "2025-11-25"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _format_log_entry(endpoint: str, method: str, params: dict = None, status: int = None, result: dict = None, error: dict = None, duration_ms: float = 0, client_id: str = None) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "logger": "mcp_service",
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "duration_ms": round(duration_ms, 2)
    }
    if client_id:
        entry["client_id"] = client_id
    if params:
        entry["params"] = params
    if result:
        entry["result"] = result
    if error:
        entry["error"] = error
    return entry


def _log_json(entry: dict) -> None:
    logger.info(json.dumps(entry))


@app.on_event("startup")
def on_startup():
    init_erp_db()
    seed_data()
    approval_manager.cleanup()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "erp-mcp-service"}


def verify_api_key(request: Request, skip_if_empty: bool = True) -> None:
    if MCP_API_KEY:
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != MCP_API_KEY:
            raise HTTPException(status_code=401, detail="Missing API Key")


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int | str | None] = None
    method: str
    params: dict = {}


def _validate_accept_header(request: Request) -> bool:
    accept = request.headers.get("Accept", "")
    has_json = "application/json" in accept
    has_sse = "text/event-stream" in accept
    if has_json or has_sse:
        return True
    client_mode = request.headers.get("x-mcp-response-mode", "").lower()
    if client_mode in ("sse", "json"):
        return True
    return False


def _build_response(request_id: str, result: Any) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def _build_error(request_id: str, code: int, message: str, data: Any = None) -> dict:
    error = {
        "code": code,
        "message": message
    }
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error
    }


def _dispatch_method(method: str, params: dict, request_id: Optional[str], session: Optional[Any] = None) -> dict:
    start_time = time.perf_counter()

    has_request_id = request_id is not None
    req_id = request_id if has_request_id else str(uuid.uuid4())

    if session and req_id:
        session.track_request(req_id)

    _log_json(_format_log_entry(
        endpoint="dispatch",
        method=method,
        params=params,
        status=0,
        result={"request_id": req_id, "has_request_id": has_request_id},
        duration_ms=(time.perf_counter() - start_time) * 1000
    ))

    if method == "initialize":
        client_version = params.get("protocolVersion", "")
        client_info = params.get("clientInfo", {})
        client_capabilities = params.get("capabilities", {})

        if client_version and client_version != PROTOCOL_VERSION:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params=params,
                status=-32602,
                error={"code": -32602, "message": "Unsupported protocol version"},
                duration_ms=duration_ms
            ))
            return _build_error(
                req_id,
                -32602,
                "Unsupported protocol version",
                {"supported": [PROTOCOL_VERSION], "requested": client_version}
            )

        result = _build_response(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
                "prompts": {},
                "logging": {},
                "tasks": {
                    "list": {},
                    "cancel": {},
                    "requests": {
                        "tools": {"call": {}}
                    }
                }
            },
            "serverInfo": {
                "name": "erp-mcp-service",
                "version": "1.0.0"
            },
            "instructions": "ERP MCP Service for inventory, order, and supplier management"
        })
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint="dispatch",
            method=method,
            params=params,
            status=200,
            result={
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": "erp-mcp-service v1.0.0",
                "session_created": True
            },
            duration_ms=duration_ms
        ))
        return result

    elif method == "notifications/initialized":
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint="dispatch",
            method=method,
            params={},
            status=202,
            result={"status": "acknowledged"},
            duration_ms=duration_ms
        ))
        return {"jsonrpc": "2.0", "id": None}

    elif method == "tools/list":
        try:
            tools = list_tools()
            result = _build_response(req_id, {"tools": tools})
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params=params,
                status=200,
                result={"tools_count": len(tools)},
                duration_ms=duration_ms
            ))
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params=params,
                status=-32603,
                error={"code": -32603, "message": str(e)},
                duration_ms=duration_ms
            ))
            return _build_error(req_id, -32603, f"Internal error: {str(e)}")

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        task_param = params.get("task")

        if not tool_name:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params=params,
                status=-32602,
                error={"code": -32602, "message": "Missing required parameter: name"},
                duration_ms=duration_ms
            ))
            return _build_error(req_id, -32602, "Missing required parameter: name")

        if task_param:
            support = get_task_support(tool_name)
            if support == "forbidden":
                duration_ms = (time.perf_counter() - start_time) * 1000
                _log_json(_format_log_entry(
                    endpoint="dispatch",
                    method=method,
                    params={"name": tool_name, "task": task_param},
                    status=-32601,
                    error={"code": -32601, "message": f"Tool {tool_name} does not support tasks"},
                    duration_ms=duration_ms
                ))
                return _build_error(req_id, -32601, f"Tool {tool_name} does not support tasks")

            ttl = task_param.get("ttl", 60000)
            task = task_manager.create_task(ttl=ttl)

            def _run_async():
                try:
                    result_data = call_tool(tool_name, arguments)
                    task_manager.complete_task(task.task_id, result_data)
                except Exception as e:
                    task_manager.fail_task(task.task_id, str(e))

            worker = threading.Thread(target=_run_async, daemon=True)
            worker.start()

            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params={"name": tool_name, "task": task_param},
                status=200,
                result={"taskId": task.task_id, "status": "working"},
                duration_ms=duration_ms
            ))
            return _build_response(req_id, {
                "task": {
                    "taskId": task.task_id,
                    "status": "working"
                }
            })

        try:
            result_data = call_tool(tool_name, arguments)
            result = _build_response(req_id, result_data)
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params={"name": tool_name, "arguments": arguments},
                status=200,
                result={"tool": tool_name},
                duration_ms=duration_ms
            ))
            return result
        except ValueError as e:
            error = e.args[0] if e.args else str(e)
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_response = None
            if hasattr(error, "code"):
                if error.code == "TOOL_NOT_FOUND":
                    error_response = _build_error(req_id, -32601, f"Tool not found: {tool_name}")
                    _log_json(_format_log_entry(
                        endpoint="dispatch",
                        method=method,
                        params={"name": tool_name, "arguments": arguments},
                        status=-32601,
                        error={"code": -32601, "message": f"Tool not found: {tool_name}"},
                        duration_ms=duration_ms
                    ))
                else:
                    error_response = _build_error(req_id, -32603, str(error.message), error.detail)
                    _log_json(_format_log_entry(
                        endpoint="dispatch",
                        method=method,
                        params={"name": tool_name, "arguments": arguments},
                        status=-32603,
                        error={"code": -32603, "message": str(error.message)},
                        duration_ms=duration_ms
                    ))
            else:
                error_response = _build_error(req_id, -32603, str(e))
                _log_json(_format_log_entry(
                    endpoint="dispatch",
                    method=method,
                    params={"name": tool_name, "arguments": arguments},
                    status=-32603,
                    error={"code": -32603, "message": str(e)},
                    duration_ms=duration_ms
                ))
            return error_response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                endpoint="dispatch",
                method=method,
                params={"name": tool_name, "arguments": arguments},
                status=-32603,
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
                duration_ms=duration_ms
            ))
            return _build_error(req_id, -32603, f"Internal error: {str(e)}")

    elif method == "tasks/status":
        task_id = params.get("taskId")
        if not task_id:
            return _build_error(req_id, -32602, "Missing required parameter: taskId")
        task_status = task_manager.get_task_status(task_id)
        if not task_status:
            return _build_error(req_id, -32602, f"Task not found or expired: {task_id}")
        return _build_response(req_id, {"task": task_status})

    elif method == "tasks/complete":
        task_id = params.get("taskId")
        if not task_id:
            return _build_error(req_id, -32602, "Missing required parameter: taskId")
        task_result = task_manager.get_task_result(task_id)
        if not task_result:
            return _build_error(req_id, -32602, f"Task not found or expired: {task_id}")
        if task_result.get("status") not in ("completed", "failed"):
            return _build_error(req_id, -32602, f"Task not yet complete: {task_result.get('status')}")
        return _build_response(req_id, task_result)

    elif method == "tasks/cancel":
        task_id = params.get("taskId")
        if not task_id:
            return _build_error(req_id, -32602, "Missing required parameter: taskId")
        if not task_manager.cancel_task(task_id):
            return _build_error(req_id, -32602, f"Task not found or not cancelable: {task_id}")
        return _build_response(req_id, {"task": {"taskId": task_id, "status": "canceled"}})

    elif method == "tasks/list":
        tasks = task_manager.list_tasks()
        return _build_response(req_id, {"tasks": tasks})

    else:
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint="dispatch",
            method=method,
            params=params,
            status=-32601,
            error={"code": -32601, "message": f"Method not found: {method}"},
            duration_ms=duration_ms
        ))
        return _build_error(req_id, -32601, f"Method not found: {method}")


async def _handle_mcp_request(request: Request) -> dict:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _build_error(None, -32600, "Invalid JSON")

    jsonrpc_req = JsonRpcRequest(**body)
    return _dispatch_method(jsonrpc_req.method, jsonrpc_req.params, jsonrpc_req.id)


def _client_accepts_sse(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/event-stream" in accept


def _build_sse_content(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: message\ndata: {payload}\n\n"


def _get_or_create_session(request: Request):
    session_id = request.headers.get("mcp-session-id")
    if session_id:
        return session_manager.get_session(session_id)
    return None


@app.post("/mcp")
@app.post("/")
async def mcp_unified_endpoint(request: Request):
    start_time = time.perf_counter()
    verify_api_key(request)

    client_id = request.headers.get("x-client-id", "anonymous")

    if not _validate_accept_header(request):
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint=request.url.path,
            method="(accept_header_validation)",
            status=400,
            error={"code": 400, "message": "Missing or invalid Accept header"},
            duration_ms=duration_ms
        ))
        return Response(
            content=json.dumps({"error": "Missing or invalid Accept header. Required: application/json, text/event-stream"}),
            status_code=400,
            media_type="application/json"
        )

    session_id = request.headers.get("mcp-session-id")
    session = None
    if session_id:
        session = session_manager.get_session(session_id)
        if not session:
            return Response(
                content=json.dumps(_build_error(None, -32000, "Session not found or expired")),
                status_code=400,
                media_type="application/json",
                headers={"MCP-Protocol-Version": PROTOCOL_VERSION}
            )

    try:
        body = await request.json()
    except json.JSONDecodeError:
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint=request.url.path,
            method="(json_parse)",
            status=400,
            error={"code": -32600, "message": "Invalid JSON"},
            duration_ms=duration_ms
        ))
        return Response(
            content=json.dumps(_build_error(None, -32600, "Invalid JSON")),
            status_code=400,
            media_type="application/json"
        )

    jsonrpc_req = JsonRpcRequest(**body)
    result = _dispatch_method(jsonrpc_req.method, jsonrpc_req.params, jsonrpc_req.id, session=session)

    if session and jsonrpc_req.id:
        session.complete_request(jsonrpc_req.id)

    if jsonrpc_req.method == "initialize":
        session = session_manager.create_session(client_id=client_id)
        session_id = session.session_id
        logger.info(f"SESSION_CREATED: session_id={session_id}, client_id={client_id}, request_id={jsonrpc_req.id}")
        logger.info(f"SESSION_CREATED: full_response_id={jsonrpc_req.id}")

    if jsonrpc_req.method == "notifications/initialized":
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint=request.url.path,
            method=jsonrpc_req.method,
            params=jsonrpc_req.params,
            status=202,
            duration_ms=duration_ms
        ))
        return Response(status_code=202, media_type="application/json")

    status_code = 200
    if "error" in result:
        status_code = 500

    duration_ms = (time.perf_counter() - start_time) * 1000
    _log_json(_format_log_entry(
        endpoint=request.url.path,
        method=jsonrpc_req.method,
        params=jsonrpc_req.params,
        status=status_code,
        duration_ms=duration_ms,
        client_id=client_id
    ))

    resp_headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}
    if session_id:
        resp_headers["Mcp-Session-Id"] = session_id

    client_mode = request.headers.get("x-mcp-response-mode", "").lower()
    effective_mode = client_mode if client_mode in ("sse", "json") else MCP_RESPONSE_MODE
    use_sse = (
        effective_mode == "sse"
        or (effective_mode == "auto" and _client_accepts_sse(request))
    )

    if use_sse:
        from starlette.responses import StreamingResponse
        import asyncio

        async def sse_stream():
            yield _build_sse_content(result)
            await asyncio.sleep(0.1)

        return StreamingResponse(
            sse_stream(),
            status_code=status_code,
            media_type="text/event-stream",
            headers=resp_headers
        )
    else:
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json",
            headers=resp_headers
        )


@app.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    verify_api_key(request)

    accept = request.headers.get("accept", "")
    if "text/event-stream" not in accept:
        return Response(status_code=405)

    session_id = request.headers.get("mcp-session-id")
    session = None
    if session_id:
        session = session_manager.get_session(session_id)

    async def event_generator():
        import asyncio
        try:
            while True:
                if session:
                    msg = session.dequeue_message(timeout=1.0)
                    if msg:
                        payload = json.dumps(msg, ensure_ascii=False)
                        yield f"event: message\ndata: {payload}\n\n"
                        continue
                yield ": ping\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass
        finally:
            if session:
                pass

    resp_headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}
    if session_id:
        resp_headers["Mcp-Session-Id"] = session_id

    from starlette.responses import StreamingResponse
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=resp_headers
    )


@app.delete("/mcp")
async def mcp_delete_session(request: Request):
    verify_api_key(request)

    session_id = request.headers.get("mcp-session-id")
    if not session_id:
        return Response(status_code=405)

    removed = session_manager.remove_session(session_id)
    if not removed:
        return Response(status_code=404)

    return Response(
        status_code=200,
        media_type="application/json",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION}
    )


@app.post("/mcp/tools/list")
async def tools_list_legacy(request: Request):
    start_time = time.perf_counter()
    verify_api_key(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint="/mcp/tools/list",
            method="(json_parse)",
            status=400,
            error={"code": -32600, "message": "Invalid JSON"},
            duration_ms=duration_ms
        ))
        return Response(
            content=json.dumps(_build_error(None, -32600, "Invalid JSON")),
            status_code=400,
            media_type="application/json"
        )

    jsonrpc_req = JsonRpcRequest(**body)
    result = _dispatch_method(jsonrpc_req.method, jsonrpc_req.params, jsonrpc_req.id)

    status_code = 200
    if "error" in result:
        status_code = 500

    duration_ms = (time.perf_counter() - start_time) * 1000
    _log_json(_format_log_entry(
        endpoint="/mcp/tools/list",
        method=jsonrpc_req.method,
        params=jsonrpc_req.params,
        status=status_code,
        duration_ms=duration_ms
    ))

    return Response(
        content=json.dumps(result),
        status_code=status_code,
        media_type="application/json",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION}
    )


@app.post("/mcp/tools/call")
async def tools_call_legacy(request: Request):
    start_time = time.perf_counter()
    verify_api_key(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        duration_ms = (time.perf_counter() - start_time) * 1000
        _log_json(_format_log_entry(
            endpoint="/mcp/tools/call",
            method="(json_parse)",
            status=400,
            error={"code": -32600, "message": "Invalid JSON"},
            duration_ms=duration_ms
        ))
        return Response(
            content=json.dumps(_build_error(None, -32600, "Invalid JSON")),
            status_code=400,
            media_type="application/json"
        )

    jsonrpc_req = JsonRpcRequest(**body)
    result = _dispatch_method(jsonrpc_req.method, jsonrpc_req.params, jsonrpc_req.id)

    status_code = 200
    if "error" in result:
        status_code = 500

    duration_ms = (time.perf_counter() - start_time) * 1000
    _log_json(_format_log_entry(
        endpoint="/mcp/tools/call",
        method=jsonrpc_req.method,
        params=jsonrpc_req.params,
        status=status_code,
        duration_ms=duration_ms
    ))

    return Response(
        content=json.dumps(result),
        status_code=status_code,
        media_type="application/json",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MCP_SERVICE_PORT)