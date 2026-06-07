import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
from requests.exceptions import ConnectionError, Timeout

from app.config import TIMEOUT_CONFIG
from app.errors import (
    mcp_service_unavailable, mcp_connection_timeout, mcp_invalid_response,
    mcp_tool_not_found, mcp_auth_failed, AgentError
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PROTOCOL_VERSION = "2025-11-25"


def _format_log_entry(method: str, params: dict = None, result: dict = None, error: dict = None, duration_ms: float = 0) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "logger": "mcp_client",
        "method": method,
        "duration_ms": round(duration_ms, 2)
    }
    if params:
        entry["params"] = params
    if result:
        entry["result"] = result
    if error:
        entry["error"] = error
    return entry


def _log_json(entry: dict) -> None:
    logger.info(json.dumps(entry))


class MCPClient:
    def __init__(
        self,
        name: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ):
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout or TIMEOUT_CONFIG["mcp_request"]
        self._client_id = str(uuid.uuid4())
        self._tools = None
        self._initialized = False
        self._server_info = None

    def _parse_sse_response(self, text: str) -> dict:
        for line in text.split("\n"):
            if line.startswith("data: "):
                payload = line[6:].strip()
                if payload:
                    return json.loads(payload)
        raise ValueError("No data found in SSE response")

    def _request(self, method: str, path: str, json_data: Optional[dict] = None) -> dict:
        url = f"{self.endpoint}{path}"
        headers = dict(self.headers)
        headers["Accept"] = "application/json, text/event-stream"
        headers["X-Client-Id"] = self._client_id

        rpc_method = json_data.get("method") if json_data else method
        start_time = time.perf_counter()

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                headers=headers,
                timeout=self.timeout
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 401:
                logger.error(f"MCP auth failed: {url} returned 401, response: {response.text[:200]}")
                raise ValueError(mcp_auth_failed(f"401 from {url}"))
            if response.status_code == 503:
                logger.error(f"MCP service unavailable: {url} returned 503, response: {response.text[:200]}")
                raise ValueError(mcp_service_unavailable(f"503 from {url}"))

            if response.status_code >= 400:
                logger.error(
                    f"MCP request failed: {url} returned {response.status_code}, "
                    f"response: {response.text[:500]}, duration_ms: {duration_ms:.2f}"
                )

            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                result = self._parse_sse_response(response.text)
            else:
                result = response.json()

            _log_json(_format_log_entry(
                method=rpc_method,
                params=json_data.get("params") if json_data else {},
                result=result,
                duration_ms=duration_ms
            ))

            return result

        except ConnectionError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"MCP ConnectionError to {self.name}: url={url}, duration_ms={duration_ms:.0f}, error={str(e)}")
            logger.error(json.dumps(_format_log_entry(
                method=rpc_method,
                params=json_data.get("params") if json_data else {},
                error={"code": "CONNECTION_ERROR", "message": str(e), "url": url},
                duration_ms=duration_ms
            )))
            raise ValueError(mcp_connection_timeout(f"Cannot connect to {self.name} at {url}"))
        except Timeout:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"MCP Timeout to {self.name}: url={url}, timeout={self.timeout}s, duration_ms={duration_ms:.0f}")
            logger.error(json.dumps(_format_log_entry(
                method=rpc_method,
                params=json_data.get("params") if json_data else {},
                error={"code": "TIMEOUT", "message": f"Timeout connecting to {self.name}", "url": url, "timeout": self.timeout},
                duration_ms=duration_ms
            )))
            raise ValueError(mcp_connection_timeout(f"Timeout connecting to {self.name} (timeout={self.timeout}s)"))
        except json.JSONDecodeError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(json.dumps(_format_log_entry(
                method=rpc_method,
                params=json_data.get("params") if json_data else {},
                error={"code": "JSON_DECODE_ERROR", "message": f"Invalid JSON from {self.name}: {str(e)}", "response_preview": response.text[:200]},
                duration_ms=duration_ms
            )))
            raise ValueError(mcp_invalid_response(f"Invalid JSON from {self.name}"))
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            if isinstance(e, ValueError) and len(e.args) == 1 and isinstance(e.args[0], AgentError):
                raise
            logger.error(json.dumps(_format_log_entry(
                method=rpc_method,
                params=json_data.get("params") if json_data else {},
                error={"code": "REQUEST_ERROR", "message": str(e), "type": type(e).__name__, "url": url},
                duration_ms=duration_ms
            )))
            raise ValueError(mcp_invalid_response(str(e)))

    def _initialize(self) -> None:
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "erp-agent",
                    "version": "1.0.0"
                }
            }
        }

        start_time = time.perf_counter()
        result = self._request("POST", "/mcp", payload)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if "error" in result:
            error_data = result["error"]
            if error_data.get("code") == -32602:
                supported = error_data.get("data", {}).get("supported", [])
                raise ValueError(mcp_invalid_response(
                    f"Protocol version mismatch. Server supports: {supported}, client: {PROTOCOL_VERSION}"
                ))
            raise ValueError(mcp_invalid_response(f"Initialize error from {self.name}: {error_data}"))

        self._server_info = result.get("result", {})
        _log_json(_format_log_entry(
            method="initialize",
            params=payload["params"],
            result={"protocolVersion": self._server_info.get("protocolVersion"), "serverInfo": self._server_info.get("serverInfo")},
            duration_ms=duration_ms
        ))

        self._send_initialized_notification()

    def _send_initialized_notification(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }

        url = f"{self.endpoint}/mcp"
        headers = dict(self.headers)
        headers["Accept"] = "application/json, text/event-stream"
        headers["X-Client-Id"] = self._client_id

        start_time = time.perf_counter()

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 202:
                _log_json(_format_log_entry(
                    method="notifications/initialized",
                    params={},
                    result={"status": "sent"},
                    duration_ms=duration_ms
                ))
            else:
                _log_json(_format_log_entry(
                    method="notifications/initialized",
                    params={},
                    error={"code": response.status_code, "message": f"Unexpected status {response.status_code}"},
                    duration_ms=duration_ms
                ))
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_json(_format_log_entry(
                method="notifications/initialized",
                params={},
                error={"code": "EXCEPTION", "message": str(e)},
                duration_ms=duration_ms
            ))

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def list_tools(self) -> List[Dict[str, Any]]:
        self._ensure_initialized()

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {}
        }

        start_time = time.perf_counter()
        result = self._request("POST", "/mcp", payload)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if "error" in result:
            raise ValueError(mcp_invalid_response(f"JSON-RPC error from {self.name}: {result['error']}"))

        tools = result.get("result", {}).get("tools", [])
        self._tools = tools

        _log_json(_format_log_entry(
            method="tools/list",
            params={},
            result={"tools_count": len(tools)},
            duration_ms=duration_ms
        ))

        return tools

    def call_tool(self, tool_name: str, arguments: dict, params: dict = None) -> dict:
        self._ensure_initialized()

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        if params:
            payload["params"].update(params)

        start_time = time.perf_counter()
        result = self._request("POST", "/mcp", payload)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if "error" in result:
            error_data = result["error"]
            _log_json(_format_log_entry(
                method="tools/call",
                params={"name": tool_name, "arguments": arguments},
                error=error_data,
                duration_ms=duration_ms
            ))
            if error_data.get("code") == -32601:
                raise ValueError(mcp_tool_not_found(tool_name))
            raise ValueError(mcp_invalid_response(f"Tool error from {self.name}: {error_data}"))

        _log_json(_format_log_entry(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
            result={"tool": tool_name},
            duration_ms=duration_ms
        ))

        return result.get("result", {})

    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.endpoint}/health",
                timeout=TIMEOUT_CONFIG["mcp_connect"]
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_tools(self) -> List[Dict[str, Any]]:
        if self._tools is None:
            self.list_tools()
        return self._tools or []

    def get_risk_level(self, tool_name: str) -> str:
        check_name = tool_name
        if tool_name.startswith("mcp_"):
            check_name = tool_name[4:]
        for tool in (self._tools or []):
            name = tool.get("name", "")
            if name == tool_name or name == check_name or name == f"mcp_{check_name}":
                metadata = tool.get("metadata", {})
                return metadata.get("riskLevel", "SAFE")
        return "SAFE"

    def execute_tool(self, name: str, args: dict) -> dict:
        return self.call_tool(name, args)

    def execute_tool_preapproved(self, name: str, args: dict, user_op_id: str = None) -> dict:
        """已审批的执行：调用 MCP 服务传入 preapproved 标志，跳过 MCP 内部审批"""
        return self.call_tool(name, args, params={
            "_meta": {
                "preapproved": True,
                "user_op_id": user_op_id
            }
        })

    def get_approval_detail(self, tool_name: str, args: dict) -> dict:
        return {
            "summary": f"执行{tool_name}",
            "detail": {"tool": tool_name, "args": args}
        }

    def refresh_tools(self) -> None:
        self._tools = None
        self.list_tools()