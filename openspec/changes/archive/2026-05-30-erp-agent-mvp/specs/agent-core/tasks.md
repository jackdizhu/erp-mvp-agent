# Agent Core — Tasks

> Spec: [specs/agent-core/spec.md](spec.md)
> Files: `/app/agent.py`, `/app/llm.py`

---

## 1. LLM 层 (llm.py)

- [x] 1.1 实现 OpenAI 客户端初始化
- [x] 1.2 实现 call_llm 函数（原生 Tool Calling API）
- [x] 1.3 实现系统提示词构建
- [x] 1.4 实现 LLM 错误包装

```python
import os
from openai import OpenAI, APITimeoutError, RateLimitError, BadRequestError
from app.errors import (
    llm_timeout, llm_overload, llm_token_limit, llm_invalid_response
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。

你可以执行以下操作：
- 查询订单状态、批量查询订单
- 查询库存信息、查询供应商信息
- 创建销售订单或采购订单
- 修改订单、取消订单、删除订单
- 调整库存数量

对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。
请用简洁专业的中文回复用户。"""

def call_llm(messages: list, tools: list = None) -> dict:
    try:
        kwargs = {
            "model": os.getenv("LLM_MODEL", "gpt-4o"),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        content = choice.message.content
        tool_calls = choice.message.tool_calls

        return {
            "finish_reason": finish_reason,
            "content": content,
            "tool_calls": tool_calls
        }

    except APITimeoutError:
        raise ValueError(llm_timeout())
    except RateLimitError:
        raise ValueError(llm_overload())
    except BadRequestError as e:
        if "token" in str(e).lower() or "length" in str(e).lower():
            raise ValueError(llm_token_limit(str(e)))
        raise ValueError(llm_invalid_response(str(e)))
    except Exception as e:
        raise ValueError(llm_invalid_response(str(e)))
```

## 2. Agent 核心循环 (agent.py)

- [x] 2.1 实现 chat 函数框架 — 构建消息、调用 LLM、路由响应
- [x] 2.2 实现直接回复路径 (finish_reason=stop)
- [x] 2.3 实现 Tool Call 路径 — 解析 tool_calls，按风险级别路由
- [x] 2.4 实现 SAFE Tool 执行
- [x] 2.5 实现 CAUTION Tool 执行（含限额检查）
- [x] 2.6 实现 DANGER Tool 执行（创建 pending_action）
- [x] 2.7 实现 confirm_action 函数
- [x] 2.8 实现历史窗口截断

```python
from app.llm import call_llm, SYSTEM_PROMPT
from app.tools import TOOL_SCHEMAS, execute_tool
from app.config import TOOL_RISK_LEVELS, TOOL_LIMITS, HISTORY_WINDOW
from app.approval import approval_manager
from app.errors import (
    tool_limit, tool_expired, build_error_response, AgentError
)

def truncate_history(history: list) -> list:
    n = HISTORY_WINDOW["default_n"]
    return history[-n:] if len(history) > n else history

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
                "reply": response["content"] or "",
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
    tool_results_content = []
    for r in results:
        if "result" in r:
            tool_results_content.append(
                f"Tool {r['tool']}({r['args']}) → {r['result']}"
            )

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
        "reply": response["content"] or "",
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
```

## 3. 辅助 import

- [x] 3.1 确认 agent.py 顶部 import 完整

```python
import json
from app.llm import call_llm, SYSTEM_PROMPT
from app.tools import TOOL_SCHEMAS, execute_tool
from app.config import TOOL_RISK_LEVELS, TOOL_LIMITS, HISTORY_WINDOW
from app.approval import approval_manager
from app.errors import (
    tool_limit, tool_expired, build_error_response,
    AgentError, llm_invalid_response
)
```
