import json
import re
import asyncio
from typing import Callable, Optional

from app.llm import call_llm, call_llm_stream, SYSTEM_PROMPT
from app.erp_client import erp_client
from app.config import HISTORY_WINDOW
from app.approval_core import approval_core
from app.intent_detector import detect_tool_intent
from app.errors import (
    tool_limit, tool_expired, build_error_response,
    AgentError, llm_invalid_response, approval_failed,
    approval_required, llm_retry_exhausted
)


def truncate_history(history: list) -> list:
    n = HISTORY_WINDOW["default_n"]
    return history[-n:] if len(history) > n else history


def _strip_think_tags(text: str) -> str:
    if not text:
        return text
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def build_messages(message: str, history: list) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in truncate_history(history):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})
    return messages


def chat(message: str, history: list) -> dict:
    try:
        messages = build_messages(message, history)
        response = call_llm(messages, erp_client.get_tools())

        if response["finish_reason"] == "stop" or not response["tool_calls"]:
            reply = _strip_think_tags(response["content"]) or ""
            expected_tool = detect_tool_intent(message)

            if expected_tool:
                return _force_tool_retry(
                    messages, message, expected_tool, reply
                )

            return {
                "reply": reply,
                "tool_calls": [],
                "pending_action": None,
                "error": None
            }

        return _handle_tool_calls(response["tool_calls"], messages)

    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        if err:
            return build_error_response(err)
        return build_error_response(llm_invalid_response(str(e)))


def _force_tool_retry(messages: list, user_message: str, expected_tool: str, previous_reply: str) -> dict:
    retry_messages = messages + [
        {"role": "assistant", "content": previous_reply},
        {
            "role": "system",
            "content": f"请使用 {expected_tool} 工具重新处理此请求。此操作需要调用工具而非直接回答。"
        }
    ]

    retry_response = call_llm(retry_messages, erp_client.get_tools())

    if retry_response["finish_reason"] == "tool_calls" and retry_response["tool_calls"]:
        return _handle_tool_calls(retry_response["tool_calls"], retry_messages)

    return build_error_response(llm_retry_exhausted(expected_tool))


def _handle_tool_calls(tool_calls, messages: list) -> dict:
    results = []
    pending = None
    has_danger = False

    for tc in tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)

        risk = erp_client.get_risk_level(tool_name)

        if risk == "SAFE":
            result = _execute_safe(tool_name, tool_args)
            results.append(result)

        elif risk == "CAUTION":
            result = _execute_caution(tool_name, tool_args)
            if isinstance(result, dict) and result.get("error"):
                return result
            results.append(result)

        elif risk == "DANGER":
            has_danger = True
            action = approval_core.create_pending(
                tool_name, tool_args, messages
            )
            if not action:
                return build_error_response(approval_failed(tool_name))
            pending = action
            results.append({
                "tool": tool_name,
                "args": tool_args,
                "status": "pending_approval",
                "action_id": action["id"]
            })

    if has_danger and not pending:
        return build_error_response(approval_required())

    if pending:
        return {
            "reply": f"需要确认以下操作：{pending['summary']}",
            "tool_calls": results,
            "pending_action": pending,
            "error": None
        }

    return _generate_reply_from_results(results, messages)


def _execute_safe(tool_name: str, tool_args: dict) -> dict:
    try:
        result = erp_client.execute_tool(tool_name, tool_args)
        return {
            "tool": tool_name,
            "args": tool_args,
            "result": result
        }
    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        return {
            "tool": tool_name,
            "args": tool_args,
            "error": err.to_dict() if err else {"message": str(e)}
        }


def _execute_caution(tool_name: str, tool_args: dict) -> dict:
    if tool_name == "create_order":
        items = tool_args.get("items", [])
        if len(items) > 5:
            err = tool_limit(tool_name, 5, len(items))
            return build_error_response(err)
    if tool_name == "update_order":
        items = tool_args.get("items", [])
        if len(items) > 5:
            err = tool_limit(tool_name, 5, len(items))
            return build_error_response(err)
    return _execute_safe(tool_name, tool_args)


def _generate_reply_from_results(results: list, messages: list) -> dict:
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": f"call_{i}", "type": "function",
                        "function": {"name": r["tool"],
                                     "arguments": json.dumps(r["args"])}}
                       for i, r in enumerate(results)]
    })
    for i, r in enumerate(results):
        messages.append({
            "role": "tool",
            "tool_call_id": f"call_{i}",
            "content": json.dumps(r.get("result", r.get("error", {})))
        })

    response = call_llm(messages)
    return {
        "reply": _strip_think_tags(response["content"]) or "",
        "tool_calls": results,
        "pending_action": None,
        "error": None
    }


def confirm_action(action_id: str, approved: bool, history: list) -> dict:
    result = approval_core.confirm(action_id, approved)

    if result is None:
        err = tool_expired(action_id)
        return build_error_response(err)

    if result.get("expired"):
        err = tool_expired(action_id)
        return build_error_response(err)

    if not result.get("approved"):
        return {
            "reply": "操作已取消",
            "tool_calls": [],
            "pending_action": None,
            "error": None
        }

    action = result["action"]
    messages = action["messages_context"]

    try:
        exec_result = erp_client.execute_tool(action["tool"], action["args"])
        tool_call_record = {
            "tool": action["tool"],
            "args": action["args"],
            "result": exec_result
        }
    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        return build_error_response(err or llm_invalid_response(str(e)))

    return _generate_reply_from_results([tool_call_record], messages)


def format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_chat(message: str, history: list, on_event: Callable[[str, dict], None]):
    try:
        messages = build_messages(message, history)

        on_event("thinking", {
            "stage": "analyzing_intent",
            "message": "正在理解您的意图..."
        })

        results = []
        pending = None
        has_danger = False

        response = call_llm(messages, erp_client.get_tools())

        if response["finish_reason"] == "stop" or not response["tool_calls"]:
            reply = _strip_think_tags(response["content"]) or ""
            expected_tool = detect_tool_intent(message)

            if expected_tool:
                _stream_force_tool_retry(
                    messages, message, expected_tool, reply, on_event
                )
                return

            on_event("reply_chunk", {"content": reply})
            on_event("done", {
                "complete": True,
                "tool_calls": [],
                "pending_action": None
            })
            return

        tool_calls_data = _handle_tool_calls_stream(
            response["tool_calls"], messages, on_event
        )

        if tool_calls_data is None:
            return

        results, pending, has_danger = tool_calls_data

        if pending:
            on_event("done", {
                "complete": True,
                "tool_calls": results,
                "pending_action": pending
            })
            return

        on_event("thinking", {
            "stage": "generating_reply",
            "message": "正在生成回复..."
        })

        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": f"call_{i}", "type": "function",
                            "function": {"name": r["tool"],
                                         "arguments": json.dumps(r["args"])}}
                           for i, r in enumerate(results)]
        })
        for i, r in enumerate(results):
            messages.append({
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": json.dumps(r.get("result", r.get("error", {})))
            })

        def _reply_chunk(chunk: str):
            on_event("reply_chunk", {"content": chunk})

        response = call_llm_stream(messages, on_chunk=_reply_chunk)

        on_event("done", {
            "complete": True,
            "tool_calls": results,
            "pending_action": None
        })

    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        if err:
            on_event("done", {
                "complete": False,
                "tool_calls": [],
                "pending_action": None,
                "error": err.to_dict()
            })
        else:
            on_event("done", {
                "complete": False,
                "tool_calls": [],
                "pending_action": None,
                "error": llm_invalid_response(str(e)).to_dict()
            })


def _handle_tool_calls_stream(tool_calls, messages: list, on_event: Callable[[str, dict], None]):
    results = []
    pending = None
    has_danger = False

    for tc in tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)

        risk = erp_client.get_risk_level(tool_name)

        on_event("tool_call", {
            "tool": tool_name,
            "args": tool_args,
            "status": "executing"
        })

        if risk == "SAFE":
            result = _execute_safe(tool_name, tool_args)
            results.append(result)

        elif risk == "CAUTION":
            result = _execute_caution(tool_name, tool_args)
            if isinstance(result, dict) and result.get("error"):
                on_event("tool_result", {
                    "tool": tool_name,
                    "result": None,
                    "status": "error",
                    "error": result.get("error")
                })
                return None
            results.append(result)

        elif risk == "DANGER":
            has_danger = True
            action = approval_core.create_pending(
                tool_name, tool_args, messages
            )
            if not action:
                on_event("done", {
                    "complete": False,
                    "tool_calls": results,
                    "pending_action": None,
                    "error": approval_failed(tool_name).to_dict()
                })
                return None
            pending = action
            results.append({
                "tool": tool_name,
                "args": tool_args,
                "status": "pending_approval",
                "action_id": action["id"]
            })

        on_event("tool_result", {
            "tool": tool_name,
            "result": results[-1].get("result"),
            "status": "completed"
        })

    if has_danger and not pending:
        on_event("done", {
            "complete": False,
            "tool_calls": results,
            "pending_action": None,
            "error": approval_required().to_dict()
        })
        return None

    if pending:
        return (results, pending, has_danger)

    return (results, None, has_danger)


def _stream_force_tool_retry(messages: list, user_message: str, expected_tool: str, previous_reply: str, on_event: Callable[[str, dict], None]):
    retry_messages = messages + [
        {"role": "assistant", "content": previous_reply},
        {
            "role": "system",
            "content": f"请使用 {expected_tool} 工具重新处理此请求。此操作需要调用工具而非直接回答。"
        }
    ]

    retry_response = call_llm(retry_messages, erp_client.get_tools())

    if retry_response["finish_reason"] == "tool_calls" and retry_response["tool_calls"]:
        tool_calls_data = _handle_tool_calls_stream(
            retry_response["tool_calls"], retry_messages, on_event
        )
        if tool_calls_data is None:
            return

        results, pending, has_danger = tool_calls_data

        if pending:
            on_event("done", {
                "complete": True,
                "tool_calls": results,
                "pending_action": pending
            })
            return

        def _reply_chunk(chunk: str):
            on_event("reply_chunk", {"content": chunk})

        messages_with_tools = retry_messages + [
            {"role": "assistant", "content": None, "tool_calls": [{"id": f"call_{i}", "type": "function", "function": {"name": r["tool"], "arguments": json.dumps(r["args"])}} for i, r in enumerate(results)]}
        ]
        for i, r in enumerate(results):
            messages_with_tools.append({
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": json.dumps(r.get("result", r.get("error", {})))
            })

        call_llm_stream(messages_with_tools, on_chunk=_reply_chunk)

        on_event("done", {
            "complete": True,
            "tool_calls": results,
            "pending_action": None
        })
    else:
        on_event("done", {
            "complete": False,
            "tool_calls": [],
            "pending_action": None,
            "error": llm_retry_exhausted(expected_tool).to_dict()
        })
