import json
import re
import asyncio
from typing import Callable, Optional
from datetime import datetime

from app.llm import call_llm, call_llm_stream
from app.clients.client_factory import client_factory
from app.config import HISTORY_WINDOW, ENABLE_SKILL
from app.approval_core import approval_core
from app.intent_detector import detect_tool_intent
from app.errors import (
    tool_limit, tool_expired, build_error_response,
    AgentError, llm_invalid_response, approval_failed,
    approval_required, llm_retry_exhausted, skill_execution_failed,
)
from app.prompt_config import build_system_prompt
from app.skills.registry import get_skill_registry
from app.skills.executor import SkillExecutor
from app.skills.base import WorkflowResult
from app.skills.observability import SkillObservability
from contextvars import ContextVar
from typing import Optional as _Opt
import inspect

# Context-local SSE event emitter (set by main.py:chat_endpoint per request)
_current_on_event: ContextVar = ContextVar("current_on_event", default=None)


def truncate_history(history: list) -> list:
    n = HISTORY_WINDOW["default_n"]
    return history[-n:] if len(history) > n else history


def _strip_think_tags(text: str) -> str:
    if not text:
        return text
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def _resolve_skill_fragments(message: str) -> str:
    """Match user message against SkillRegistry; return matched skill's prompt_fragment.

    Returns empty string when no skill is matched or when ENABLE_SKILL is False.
    Decision D3: Skill matching takes priority; on no match the agent falls back to
    detect_tool_intent (handled by caller).
    """
    if not ENABLE_SKILL:
        return ""
    registry = get_skill_registry()
    if not registry:
        return ""
    matched = registry.match_skill(message)
    return matched.prompt_fragment if matched else ""


def build_messages(message: str, history: list, skill_fragments: str = "") -> list:
    """Build message list for LLM. skill_fragments is injected into system prompt."""
    system_prompt = build_system_prompt(skill_fragments)
    messages = [{"role": "system", "content": system_prompt}]
    for h in truncate_history(history):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})
    return messages


def _handle_skill_approval(workflow_result: WorkflowResult, messages: list, logger=None) -> dict:
    """Bridge a Skill's need_approval result to the existing approval flow.

    Bridge contract (decision D3): handler returns intermediate_data with three keys
    (tool, tool_args, approval_summary); this function translates that into an
    approval_core.create_pending call. The handler itself does NOT import
    approval_core (kept decoupled for testability).
    """
    intermediate = workflow_result.intermediate_data or {}
    tool = intermediate.get("tool")
    tool_args = intermediate.get("tool_args")
    approval_summary = intermediate.get("approval_summary")

    if not tool or tool_args is None or not approval_summary:
        skill_name = intermediate.get("skill_name", "unknown")
        if logger:
            logger.log_error("skill_approval_contract_missing",
                             f"intermediate_data missing required keys: tool={bool(tool)}, tool_args={tool_args is not None}, approval_summary={bool(approval_summary)}")
        return build_error_response(
            skill_execution_failed(skill_name, "missing approval contract")
        )

    action = approval_core.create_pending(tool, tool_args, messages)
    if not action:
        return build_error_response(approval_failed(tool))

    if logger:
        logger.log_approval_pending(action["action_id"], action["summary"])

    return {
        "reply": f"需要确认以下操作：{approval_summary}",
        "tool_calls": [{
            "tool": tool,
            "args": tool_args,
            "status": "pending_approval",
            "action_id": action["action_id"],
        }],
        "pending_action": action,
        "error": None,
    }


def _format_intermediate_for_llm(intermediate_data: dict) -> str:
    """Format intermediate_data for system prompt injection (need_more_info path).

    Truncates to 2000 chars per spec. Larger content is replaced with a notice.
    """
    try:
        text = json.dumps(intermediate_data, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(intermediate_data)
    if len(text) > 2000:
        return text[:2000] + "\n...（数据过长，已省略）"
    return text


def chat(message: str, history: list, logger=None) -> dict:
    start_time = datetime.now()

    if logger:
        logger.log_session_start(message)

    # Skill matching (decision D3)
    skill_fragments = _resolve_skill_fragments(message)
    matched_skill = None
    workflow_result = None
    if skill_fragments:
        registry = get_skill_registry()
        matched_skill = registry.match_skill(message) if registry else None

    if matched_skill:
        # Skill observability (design D1): single instance per execution
        obs = SkillObservability(
            skill=matched_skill,
            logger=logger,
            on_event=_current_on_event.get(),
        )
        obs.skill_matched(prompt_fragment=matched_skill.prompt_fragment or "")

        # Optional: audit trail for skill fragment injection
        if logger and skill_fragments:
            logger.log_skill_fragment_applied(
                fragment_preview=skill_fragments,
                fragment_length=len(skill_fragments),
            )

        # Execute skill workflow (Python handler or YAML)
        executor = SkillExecutor()
        # Extract tool names - support both MCP format {name: ...} and OpenAI format {function: {name: ...}}
        all_tools = client_factory.get_all_tools()
        available_tools = []
        for t in all_tools:
            if "name" in t:
                available_tools.append(t["name"])
            elif "function" in t and "name" in t["function"]:
                available_tools.append(t["function"]["name"])
        try:
            workflow_result = executor.execute(
                matched_skill,
                message,
                context={"messages": None, "client_factory": client_factory},
                available_tools=available_tools,
                on_step_complete=lambda step_def, status, result, error, elapsed_ms: obs.workflow_step(
                    step_id=step_def.get("id", "unknown"),
                    type=step_def.get("type", "tool_call"),
                    status=status,
                    tool=step_def.get("tool"),
                    instruction=step_def.get("instruction"),
                    elapsed_ms=elapsed_ms,
                    result_summary=(str(result)[:80] if result is not None else None),
                    error=error,
                ),
            )
        except Exception as e:
            workflow_result = WorkflowResult(success=False, error=str(e))
            obs.skill_failed("SKILL_EXECUTION_FAILED", str(e))

        # Branch 1: need_approval → bridge
        if workflow_result and workflow_result.success and workflow_result.need_approval:
            # build_messages is called below for tool result rendering, but we need
            # the messages list for approval_core.create_pending
            messages = build_messages(message, history, skill_fragments=skill_fragments)
            workflow_result.intermediate_data = workflow_result.intermediate_data or {}
            workflow_result.intermediate_data["skill_name"] = matched_skill.name
            obs.workflow_result(success=True, need_approval=True, need_more_info=False)
            result = _handle_skill_approval(workflow_result, messages, logger)
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            return result

        # Branch 2: need_more_info → inject context, LLM continues
        if workflow_result and workflow_result.success and workflow_result.need_more_info:
            context_str = _format_intermediate_for_llm(workflow_result.intermediate_data or {})
            messages = build_messages(message, history, skill_fragments=skill_fragments)
            messages.append({
                "role": "system",
                "content": (
                    f"Skill '{matched_skill.name}' 已执行部分步骤，当前状态：\n"
                    f"{context_str}\n"
                    f"请基于以上信息继续与用户对话以补充必要信息。"
                ),
            })
            obs.workflow_result(success=True, need_approval=False, need_more_info=True)
            # Call LLM without tools
            try:
                response = call_llm(messages, None)
                if logger:
                    logger.log_llm_response(
                        response.get("finish_reason", ""),
                        response.get("content", ""),
                        response.get("tool_calls"),
                    )
                reply = _strip_think_tags(response.get("content", "")) or ""
                if logger:
                    logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
                return {
                    "reply": reply,
                    "tool_calls": [],
                    "pending_action": None,
                    "error": None,
                }
            except Exception as e:
                if logger:
                    logger.log_error("need_more_info_llm_failed", str(e))
                    logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
                return build_error_response(skill_execution_failed(matched_skill.name, str(e)))

        # Branch 3: failure → return SKILL_EXECUTION_FAILED (no fallback)
        if workflow_result and not workflow_result.success:
            obs.skill_failed(
                error_code="SKILL_EXECUTION_FAILED",
                error_detail=workflow_result.error or "unknown error",
            )
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            return build_error_response(
                skill_execution_failed(matched_skill.name, workflow_result.error or "unknown error")
            )

        # Branch 4: workflow_result is None (no workflow, prompt only) — fall through
        # to normal LLM call with skill_fragments injected
        if workflow_result and workflow_result.success:
            obs.workflow_result(success=True, need_approval=False, need_more_info=False)

    try:
        messages = build_messages(message, history, skill_fragments=skill_fragments)

        if logger:
            logger.log_llm_request(messages, client_factory.get_all_tools())

        response = call_llm(messages, client_factory.get_all_tools())

        if logger:
            logger.log_llm_response(
                response.get("finish_reason", ""),
                response.get("content", ""),
                response.get("tool_calls")
            )

        if response["finish_reason"] == "stop" or not response["tool_calls"]:
            reply = _strip_think_tags(response["content"]) or ""
            expected_tool = detect_tool_intent(message)

            if expected_tool:
                result = _force_tool_retry(
                    messages, message, expected_tool, reply, logger
                )
                if logger:
                    logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
                return result

            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            return {
                "reply": reply,
                "tool_calls": [],
                "pending_action": None,
                "error": None
            }

        result = _handle_tool_calls(response["tool_calls"], messages, logger)
        if logger:
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
        return result

    except ValueError as e:
        if logger:
            logger.log_error("ValueError", str(e))
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        if err:
            return build_error_response(err)
        return build_error_response(llm_invalid_response(str(e)))
    except Exception as e:
        if logger:
            logger.log_error("Exception", str(e))
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
        return build_error_response(llm_invalid_response(str(e)))


def _force_tool_retry(messages: list, user_message: str, expected_tool: str, previous_reply: str, logger=None) -> dict:
    retry_messages = messages + [
        {"role": "assistant", "content": previous_reply},
        {
            "role": "system",
            "content": f"请使用 {expected_tool} 工具重新处理此请求。此操作需要调用工具而非直接回答。"
        }
    ]

    if logger:
        logger.log_llm_request(retry_messages, client_factory.get_all_tools())

    retry_response = call_llm(retry_messages, client_factory.get_all_tools())

    if logger:
        logger.log_llm_response(
            retry_response.get("finish_reason", ""),
            retry_response.get("content", ""),
            retry_response.get("tool_calls")
        )

    if retry_response["finish_reason"] == "tool_calls" and retry_response["tool_calls"]:
        return _handle_tool_calls(retry_response["tool_calls"], retry_messages, logger)

    return build_error_response(llm_retry_exhausted(expected_tool))


def _handle_tool_calls(tool_calls, messages: list, logger=None) -> dict:
    results = []
    pending = None
    has_danger = False

    for tc in tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)

        risk = client_factory.get_risk_level(tool_name)

        if logger:
            logger.log_tool_call(tool_name, tool_args, risk)

        if risk == "SAFE":
            result = _execute_safe(tool_name, tool_args, logger)
            results.append(result)

        elif risk == "CAUTION":
            result = _execute_caution(tool_name, tool_args, logger)
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
            if logger:
                logger.log_approval_pending(action["action_id"], action["summary"])
            results.append({
                "tool": tool_name,
                "args": tool_args,
                "status": "pending_approval",
                "action_id": action["action_id"]
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

    return _generate_reply_from_results(results, messages, logger)


def _execute_safe(tool_name: str, tool_args: dict, logger=None) -> dict:
    try:
        result = client_factory.execute_tool(tool_name, tool_args)
        if logger:
            logger.log_tool_result(tool_name, result=result)
        return {
            "tool": tool_name,
            "args": tool_args,
            "result": result
        }
    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        error_dict = err.to_dict() if err else {"message": str(e)}
        if logger:
            logger.log_tool_result(tool_name, error=error_dict)
        return {
            "tool": tool_name,
            "args": tool_args,
            "error": error_dict
        }


def _execute_caution(tool_name: str, tool_args: dict, logger=None) -> dict:
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
    return _execute_safe(tool_name, tool_args, logger)


def _generate_reply_from_results(results: list, messages: list, logger=None) -> dict:
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

    if logger:
        logger.log_llm_request(messages)

    response = call_llm(messages)

    if logger:
        logger.log_llm_response(
            response.get("finish_reason", ""),
            response.get("content", ""),
            None
        )

    return {
        "reply": _strip_think_tags(response["content"]) or "",
        "tool_calls": results,
        "pending_action": None,
        "error": None
    }


def confirm_action(action_id: str, approved: bool, history: list, user_op_id: str = None, logger=None) -> dict:
    result = approval_core.confirm(action_id, approved, user_op_id)

    if logger:
        logger.log_approval_result(action_id, approved)

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
    tool_name = action["tool"]
    tool_args = action["args"]

    try:
        # 路由模式判断：MCP 工具走 preapproved 路径，ERP 工具走 client_factory
        mcp_alias = client_factory._mcp_tool_alias.get(tool_name)
        if mcp_alias:
            mcp_client = client_factory.get_client_for_tool(mcp_alias)
            if mcp_client and hasattr(mcp_client, "execute_tool_preapproved"):
                exec_result = mcp_client.execute_tool_preapproved(
                    tool_name, tool_args, user_op_id=user_op_id
                )
            else:
                exec_result = client_factory.execute_tool(tool_name, tool_args)
        else:
            exec_result = client_factory.execute_tool(tool_name, tool_args)

        tool_call_record = {
            "tool": tool_name,
            "args": tool_args,
            "result": exec_result
        }
    except ValueError as e:
        err = e.args[0] if isinstance(e.args[0], AgentError) else None
        return build_error_response(err or llm_invalid_response(str(e)))

    return _generate_reply_from_results([tool_call_record], messages, logger)


def format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_chat(message: str, history: list, on_event: Callable[[str, dict], None], logger=None):
    start_time = datetime.now()

    if logger:
        logger.log_session_start(message)

    # Skill matching (decision D3) - same logic as chat()
    skill_fragments = _resolve_skill_fragments(message)
    matched_skill = None
    workflow_result = None
    if skill_fragments:
        registry = get_skill_registry()
        matched_skill = registry.match_skill(message) if registry else None

    if matched_skill:
        # Skill observability: use on_event directly (not contextvars)
        obs = SkillObservability(
            skill=matched_skill,
            logger=logger,
            on_event=on_event,
        )
        obs.skill_matched(prompt_fragment=matched_skill.prompt_fragment or "")

        if logger and skill_fragments:
            logger.log_skill_fragment_applied(
                fragment_preview=skill_fragments,
                fragment_length=len(skill_fragments),
            )

        # Execute skill workflow
        executor = SkillExecutor()
        all_tools = client_factory.get_all_tools()
        available_tools = []
        for t in all_tools:
            if "name" in t:
                available_tools.append(t["name"])
            elif "function" in t and "name" in t["function"]:
                available_tools.append(t["function"]["name"])
        try:
            workflow_result = executor.execute(
                matched_skill,
                message,
                context={"messages": None, "client_factory": client_factory},
                available_tools=available_tools,
                on_step_complete=lambda step_def, status, result, error, elapsed_ms: obs.workflow_step(
                    step_id=step_def.get("id", "unknown"),
                    type=step_def.get("type", "tool_call"),
                    status=status,
                    tool=step_def.get("tool"),
                    instruction=step_def.get("instruction"),
                    elapsed_ms=elapsed_ms,
                    result_summary=(str(result)[:80] if result is not None else None),
                    error=error,
                ),
            )
        except Exception as e:
            workflow_result = WorkflowResult(success=False, error=str(e))
            obs.skill_failed("SKILL_EXECUTION_FAILED", str(e))

        # Branch 1: need_approval → bridge (same as chat())
        if workflow_result and workflow_result.success and workflow_result.need_approval:
            messages = build_messages(message, history, skill_fragments=skill_fragments)
            workflow_result.intermediate_data = workflow_result.intermediate_data or {}
            workflow_result.intermediate_data["skill_name"] = matched_skill.name
            obs.workflow_result(success=True, need_approval=True, need_more_info=False)
            result = _handle_skill_approval(workflow_result, messages, logger)
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            # Emit SSE done event for stream
            on_event("done", {
                "complete": True,
                "tool_calls": result.get("tool_calls", []),
                "pending_action": result.get("pending_action"),
            })
            return

        # Branch 2: failure → return error (same as chat())
        if workflow_result and not workflow_result.success:
            obs.skill_failed(
                error_code="SKILL_EXECUTION_FAILED",
                error_detail=workflow_result.error or "unknown error",
            )
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            on_event("done", {
                "complete": False,
                "tool_calls": [],
                "pending_action": None,
                "error": {"code": "SKILL_EXECUTION_FAILED", "message": f"技能 {matched_skill.name} 执行失败：{workflow_result.error or 'unknown error'}"}
            })
            return

        # Branch 3: workflow_result is None (prompt only) or success — fall through to LLM
        if workflow_result and workflow_result.success:
            obs.workflow_result(success=True, need_approval=False, need_more_info=False)

    try:
        messages = build_messages(message, history, skill_fragments=skill_fragments)

        on_event("thinking", {
            "stage": "analyzing_intent",
            "message": "正在理解您的意图..."
        })

        results = []
        pending = None
        has_danger = False

        if logger:
            logger.log_llm_request(messages, client_factory.get_all_tools())

        response = call_llm(messages, client_factory.get_all_tools())

        if logger:
            logger.log_llm_response(
                response.get("finish_reason", ""),
                response.get("content", ""),
                response.get("tool_calls")
            )

        if response["finish_reason"] == "stop" or not response["tool_calls"]:
            reply = _strip_think_tags(response["content"]) or ""
            expected_tool = detect_tool_intent(message)

            if expected_tool:
                _stream_force_tool_retry(
                    messages, message, expected_tool, reply, on_event, logger
                )
                return

            on_event("reply_chunk", {"content": reply})
            on_event("done", {
                "complete": True,
                "tool_calls": [],
                "pending_action": None
            })
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            return

        tool_calls_data = _handle_tool_calls_stream(
            response["tool_calls"], messages, on_event, logger
        )

        if tool_calls_data is None:
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
            return

        results, pending, has_danger = tool_calls_data

        if pending:
            on_event("done", {
                "complete": True,
                "tool_calls": results,
                "pending_action": pending
            })
            if logger:
                logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
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
            if logger:
                logger.log_stream_chunk(chunk)
            on_event("reply_chunk", {"content": chunk})

        response = call_llm_stream(messages, on_chunk=_reply_chunk)

        if logger:
            logger.log_llm_response(
                response.get("finish_reason", ""),
                response.get("content", ""),
                None
            )

        on_event("done", {
            "complete": True,
            "tool_calls": results,
            "pending_action": None
        })
        if logger:
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))

    except ValueError as e:
        if logger:
            logger.log_error("ValueError", str(e))
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
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
    except Exception as e:
        if logger:
            logger.log_error("Exception", str(e))
            logger.log_session_end(int((datetime.now() - start_time).total_seconds() * 1000))
        on_event("done", {
            "complete": False,
            "tool_calls": [],
            "pending_action": None,
            "error": llm_invalid_response(str(e)).to_dict()
        })


def _handle_tool_calls_stream(tool_calls, messages: list, on_event: Callable[[str, dict], None], logger=None):
    results = []
    pending = None
    has_danger = False

    for tc in tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)

        risk = client_factory.get_risk_level(tool_name)

        on_event("tool_call", {
            "tool": tool_name,
            "args": tool_args,
            "status": "executing"
        })

        if logger:
            logger.log_tool_call(tool_name, tool_args, risk)

        if risk == "SAFE":
            result = _execute_safe(tool_name, tool_args, logger)
            results.append(result)

        elif risk == "CAUTION":
            result = _execute_caution(tool_name, tool_args, logger)
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
                if logger:
                    logger.log_error("approval_failed", f"Failed to create pending action for {tool_name}")
                on_event("done", {
                    "complete": False,
                    "tool_calls": results,
                    "pending_action": None,
                    "error": approval_failed(tool_name).to_dict()
                })
                return None
            pending = action
            if logger:
                logger.log_approval_pending(action["action_id"], action["summary"])
            results.append({
                "tool": tool_name,
                "args": tool_args,
                "status": "pending_approval",
                "action_id": action["action_id"]
            })

        else:
            if logger:
                logger.log_error("unknown_risk", f"Unknown risk level '{risk}' for tool '{tool_name}', treating as SAFE")
            result = _execute_safe(tool_name, tool_args, logger)
            results.append(result)

        on_event("tool_result", {
            "tool": tool_name,
            "result": results[-1].get("result"),
            "status": "completed"
        })
        if logger:
            logger.log_tool_result(
                tool_name,
                result=results[-1].get("result"),
                error=results[-1].get("error")
            )

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


def _stream_force_tool_retry(messages: list, user_message: str, expected_tool: str, previous_reply: str, on_event: Callable[[str, dict], None], logger=None):
    retry_messages = messages + [
        {"role": "assistant", "content": previous_reply},
        {
            "role": "system",
            "content": f"请使用 {expected_tool} 工具重新处理此请求。此操作需要调用工具而非直接回答。"
        }
    ]

    if logger:
        logger.log_llm_request(retry_messages, client_factory.get_all_tools())

    retry_response = call_llm(retry_messages, client_factory.get_all_tools())

    if logger:
        logger.log_llm_response(
            retry_response.get("finish_reason", ""),
            retry_response.get("content", ""),
            retry_response.get("tool_calls")
        )

    if retry_response["finish_reason"] == "tool_calls" and retry_response["tool_calls"]:
        tool_calls_data = _handle_tool_calls_stream(
            retry_response["tool_calls"], retry_messages, on_event, logger
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
            if logger:
                logger.log_stream_chunk(chunk)
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