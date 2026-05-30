from dataclasses import dataclass


@dataclass
class ErpError:
    code: str
    message: str
    detail: str
    recoverable: bool

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "recoverable": self.recoverable
        }


def data_not_found(entity: str, entity_id: str) -> ErpError:
    return ErpError(
        code="DATA_NOT_FOUND",
        message=f"未找到{entity}{entity_id}的记录",
        detail=f"{entity} '{entity_id}' not found",
        recoverable=True
    )


def data_insufficient(item_name: str, available: int, requested: int, unit: str = "台") -> ErpError:
    return ErpError(
        code="DATA_INSUFFICIENT",
        message=f"{item_name}库存不足，当前可用{available}{unit}",
        detail=f"available={available}, requested={requested}",
        recoverable=True
    )


def data_conflict(entity: str, entity_id: str, reason: str) -> ErpError:
    return ErpError(
        code="DATA_CONFLICT",
        message=reason,
        detail=f"{entity} '{entity_id}' conflict: {reason}",
        recoverable=False
    )


def data_invalid_supplier(supplier_id: str) -> ErpError:
    return ErpError(
        code="DATA_INVALID_SUPPLIER",
        message=f"未找到供应商{supplier_id}",
        detail=f"Supplier '{supplier_id}' not found",
        recoverable=True
    )


def tool_not_found(tool_name: str) -> ErpError:
    return ErpError(
        code="TOOL_NOT_FOUND",
        message=f"不支持此操作: {tool_name}",
        detail=f"Tool '{tool_name}' not in TOOL_REGISTRY",
        recoverable=False
    )


def tool_invalid_param(tool_name: str, param: str, reason: str) -> ErpError:
    return ErpError(
        code="TOOL_INVALID_PARAM",
        message=f"参数{param}格式不正确: {reason}",
        detail=f"Tool '{tool_name}' invalid param '{param}': {reason}",
        recoverable=True
    )


def tool_limit(tool_name: str, max_items: int, requested: int) -> ErpError:
    return ErpError(
        code="TOOL_LIMIT",
        message=f"单次最多创建{max_items}条，当前请求{requested}条，请分批操作",
        detail=f"Tool '{tool_name}' limit={max_items}, requested={requested}",
        recoverable=True
    )


def sys_error(detail: str = "") -> ErpError:
    return ErpError(
        code="SYS_ERROR",
        message="系统异常，请联系管理员",
        detail=detail,
        recoverable=False
    )
