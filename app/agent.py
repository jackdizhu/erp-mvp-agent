import json
import re

from app.llm import call_llm, SYSTEM_PROMPT
from app.tools import TOOL_SCHEMAS, execute_tool
from app.config import TOOL_RISK_LEVELS, TOOL_LIMITS, HISTORY_WINDOW
from app.approval import approval_manager
from app.errors import (
    tool_limit, tool_expired, build_error_response,
    AgentError, llm_invalid_response
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
        response = call_llm(messages, TOOL_SCHEMAS)

        if response["finish_reason"] == "stop" or not response["tool_calls"]:
            return {
                "reply": _strip_think_tags(response["content"]) or "",
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


def _handle_tool_calls(tool_calls, messages: list) -> dict:
    results = []
    pending = None

    for tc in tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)

        risk = TOOL_RISK_LEVELS.get(tool_name, "SAFE")

        if risk == "SAFE":
            result = _execute_safe(tool_name, tool_args)
            results.append(result)

        elif risk == "CAUTION":
            result = _execute_caution(tool_name, tool_args)
            if isinstance(result, dict) and result.get("error"):
                return result
            results.append(result)

        elif risk == "DANGER":
            action = approval_manager.create_pending(
                tool_name, tool_args, messages
            )
            if action:
                pending = action
                results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "status": "pending_approval",
                    "action_id": action["id"]
                })

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
        result = execute_tool(tool_name, tool_args)
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
    limits = TOOL_LIMITS.get(tool_name, {})
    if "max_items" in limits:
        items = tool_args.get("items", [])
        if len(items) > limits["max_items"]:
            err = tool_limit(tool_name, limits["max_items"], len(items))
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
    result = approval_manager.confirm(action_id, approved)

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
        exec_result = execute_tool(action["tool"], action["args"])
        tool_call_record = {
            "tool": action["tool"],
            "args": action["args"],
            "result": exec_result
        }
    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        return build_error_response(err or llm_invalid_response(str(e)))

    return _generate_reply_from_results([tool_call_record], messages)
