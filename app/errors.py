from dataclasses import dataclass


@dataclass
class AgentError:
    code: str
    message: str
    detail: str
    source: str
    recoverable: bool

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "source": self.source,
            "recoverable": self.recoverable
        }

    def to_api_error(self) -> dict:
        return {
            "code": self.code,
            "recoverable": self.recoverable
        }


def llm_timeout(detail: str = "") -> AgentError:
    return AgentError(
        code="LLM_TIMEOUT",
        message="AI服务暂时不可用，请稍后重试",
        detail=detail,
        source="llm",
        recoverable=True
    )


def llm_overload(detail: str = "") -> AgentError:
    return AgentError(
        code="LLM_OVERLOAD",
        message="AI服务繁忙，请稍后重试",
        detail=detail,
        source="llm",
        recoverable=True
    )


def llm_token_limit(detail: str = "") -> AgentError:
    return AgentError(
        code="LLM_TOKEN_LIMIT",
        message="请求内容过长，请缩短后重试",
        detail=detail,
        source="llm",
        recoverable=True
    )


def llm_invalid_response(detail: str = "") -> AgentError:
    return AgentError(
        code="LLM_INVALID_RESPONSE",
        message="AI返回异常，请重新提问",
        detail=detail,
        source="llm",
        recoverable=True
    )


def tool_not_found(tool_name: str) -> AgentError:
    return AgentError(
        code="TOOL_NOT_FOUND",
        message=f"不支持此操作: {tool_name}",
        detail=f"Tool '{tool_name}' not in TOOL_REGISTRY",
        source="tool",
        recoverable=False
    )


def tool_missing_param(tool_name: str, param: str) -> AgentError:
    return AgentError(
        code="TOOL_MISSING_PARAM",
        message=f"请提供{param}",
        detail=f"Tool '{tool_name}' missing required param '{param}'",
        source="tool",
        recoverable=True
    )


def tool_invalid_param(tool_name: str, param: str, reason: str) -> AgentError:
    return AgentError(
        code="TOOL_INVALID_PARAM",
        message=f"参数{param}格式不正确: {reason}",
        detail=f"Tool '{tool_name}' invalid param '{param}': {reason}",
        source="tool",
        recoverable=True
    )


def tool_limit(tool_name: str, max_items: int, requested: int) -> AgentError:
    return AgentError(
        code="TOOL_LIMIT",
        message=f"单次最多创建{max_items}条，当前请求{requested}条，请分批操作",
        detail=f"Tool '{tool_name}' limit={max_items}, requested={requested}",
        source="tool",
        recoverable=True
    )


def tool_expired(action_id: str) -> AgentError:
    return AgentError(
        code="TOOL_EXPIRED",
        message="操作已过期，请重新发起",
        detail=f"Pending action '{action_id}' has expired",
        source="tool",
        recoverable=True
    )


def data_not_found(entity: str, entity_id: str) -> AgentError:
    return AgentError(
        code="DATA_NOT_FOUND",
        message=f"未找到{entity}{entity_id}的记录",
        detail=f"{entity} '{entity_id}' not found",
        source="data",
        recoverable=True
    )


def data_insufficient(item_name: str, available: int, requested: int, unit: str = "台") -> AgentError:
    return AgentError(
        code="DATA_INSUFFICIENT",
        message=f"{item_name}库存不足，当前可用{available}{unit}",
        detail=f"available={available}, requested={requested}",
        source="data",
        recoverable=True
    )


def data_conflict(entity: str, entity_id: str, reason: str) -> AgentError:
    return AgentError(
        code="DATA_CONFLICT",
        message=reason,
        detail=f"{entity} '{entity_id}' conflict: {reason}",
        source="data",
        recoverable=False
    )


def data_invalid_supplier(supplier_id: str) -> AgentError:
    return AgentError(
        code="DATA_INVALID_SUPPLIER",
        message=f"未找到供应商{supplier_id}",
        detail=f"Supplier '{supplier_id}' not found",
        source="data",
        recoverable=True
    )


def approval_failed(tool_name: str) -> AgentError:
    return AgentError(
        code="APPROVAL_FAILED",
        message="高风险操作审批创建失败，请联系管理员",
        detail=f"Failed to create pending action for {tool_name}",
        source="approval",
        recoverable=False
    )


def approval_required() -> AgentError:
    return AgentError(
        code="APPROVAL_REQUIRED",
        message="此操作需要审批确认，但审批创建失败",
        detail="DANGER tool executed without pending action",
        source="approval",
        recoverable=False
    )


def llm_retry_exhausted(expected_tool: str) -> AgentError:
    return AgentError(
        code="LLM_RETRY_EXHAUSTED",
        message="AI无法正确使用工具，请换种方式描述",
        detail=f"LLM still failed to call {expected_tool} after retry",
        source="llm",
        recoverable=True
    )


def sys_timeout(detail: str = "") -> AgentError:
    return AgentError(
        code="SYS_TIMEOUT",
        message="请求超时，请稍后重试",
        detail=detail,
        source="system",
        recoverable=True
    )


def sys_error(detail: str = "") -> AgentError:
    return AgentError(
        code="SYS_ERROR",
        message="系统异常，请联系管理员",
        detail=detail,
        source="system",
        recoverable=False
    )


def build_error_response(error: AgentError, reply: str = "") -> dict:
    if not reply:
        reply = error.message
    return {
        "reply": reply,
        "error": error.to_api_error(),
        "tool_calls": []
    }
