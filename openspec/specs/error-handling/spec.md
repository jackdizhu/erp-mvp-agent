## Purpose

Define the unified error model, error code taxonomy across all layers, and error propagation behavior for the ERP agent.

## Requirements

### Requirement: Unified AgentError model
The system SHALL define an AgentError class with code (str), message (str), detail (str), source (str: llm/tool/data/system), and recoverable (bool) fields.

#### Scenario: AgentError constructed
- **WHEN** a tool execution fails with "订单不存在"
- **THEN** AgentError is created with code="DATA_NOT_FOUND", message="未找到订单999的记录", source="data", recoverable=true

### Requirement: LLM layer error codes
The system SHALL define error codes with LLM_ prefix for AI layer failures: LLM_TIMEOUT, LLM_OVERLOAD, LLM_TOKEN_LIMIT, LLM_INVALID_RESPONSE.

#### Scenario: LLM API timeout
- **WHEN** OpenAI API call times out
- **THEN** system returns AgentError with code=LLM_TIMEOUT, message="AI服务暂时不可用，请稍后重试", recoverable=true

#### Scenario: LLM token limit exceeded
- **WHEN** request exceeds model's token limit
- **THEN** system returns AgentError with code=LLM_TOKEN_LIMIT, message="请求内容过长，请缩短后重试", recoverable=true

#### Scenario: LLM returns invalid format
- **WHEN** LLM response cannot be parsed
- **THEN** system returns AgentError with code=LLM_INVALID_RESPONSE, message="AI返回异常，请重新提问", recoverable=true

### Requirement: Tool layer error codes
The system SHALL define error codes with TOOL_ prefix for tool layer failures: TOOL_NOT_FOUND, TOOL_MISSING_PARAM, TOOL_INVALID_PARAM, TOOL_LIMIT, TOOL_EXPIRED.

#### Scenario: Tool not found
- **WHEN** LLM returns tool_call for a non-existent tool
- **THEN** system returns AgentError with code=TOOL_NOT_FOUND, message="不支持此操作", source="tool"

#### Scenario: Tool missing parameter
- **WHEN** tool_call for query_order is missing order_id
- **THEN** system returns AgentError with code=TOOL_MISSING_PARAM, message="请提供订单编号", source="tool"

#### Scenario: Tool limit exceeded
- **WHEN** create_order is called with qty exceeding max_items
- **THEN** system returns AgentError with code=TOOL_LIMIT, message="单次最多创建5条，请分批操作", source="tool", recoverable=true

### Requirement: Data layer error codes
The system SHALL define error codes with DATA_ prefix for data layer failures: DATA_NOT_FOUND, DATA_INSUFFICIENT, DATA_CONFLICT, DATA_INVALID_SUPPLIER.

#### Scenario: Order not found
- **WHEN** query_order("999") is called and order 999 does not exist
- **THEN** system returns AgentError with code=DATA_NOT_FOUND, message="未找到订单999的记录", source="data"

#### Scenario: Insufficient inventory
- **WHEN** create_order requests 100 units but only 40 available
- **THEN** system returns AgentError with code=DATA_INSUFFICIENT, message="iPhone 15库存不足，当前可40台", source="data"

#### Scenario: Order status conflict
- **WHEN** cancel_order is called on a delivered order
- **THEN** system returns AgentError with code=DATA_CONFLICT, message="订单123已签收，无法取消", source="data"

#### Scenario: Invalid supplier
- **WHEN** create_order references non-existent supplier
- **THEN** system returns AgentError with code=DATA_INVALID_SUPPLIER, message="未找到供应商XXX", source="data"

### Requirement: Approval layer error codes
The system SHALL define error codes with APPROVAL_ prefix for approval flow failures: APPROVAL_FAILED, APPROVAL_REQUIRED.

#### Scenario: Approval creation failed
- **WHEN** `approval_manager.create_pending()` returns None for a DANGER tool
- **THEN** system returns AgentError with code=APPROVAL_FAILED, message="高风险操作审批创建失败，请联系管理员", source="approval", recoverable=false

#### Scenario: DANGER tool executed without pending action
- **WHEN** code logic error causes DANGER tool to execute without creating pending_action
- **THEN** system returns AgentError with code=APPROVAL_REQUIRED, message="此操作需要审批确认，但审批创建失败", source="approval", recoverable=false

### Requirement: Tool call validation error codes
The system SHALL define error codes for tool call validation failures, including LLM_RETRY_EXHAUSTED for cases where LLM fails to use the correct tool after retry.

#### Scenario: LLM retry exhausted after hallucination
- **WHEN** LLM retry after hallucination still returns no tool_calls
- **THEN** system returns AgentError with code=LLM_RETRY_EXHAUSTED, message="AI无法正确使用工具，请换种方式描述", source="llm", recoverable=true

### Requirement: System layer error codes
The system SHALL define error codes with SYS_ prefix for system failures: SYS_TIMEOUT, SYS_ERROR.

#### Scenario: Network timeout
- **WHEN** HTTP request to backend times out
- **THEN** system returns AgentError with code=SYS_TIMEOUT, message="请求超时，请稍后重试", source="system", recoverable=true

### Requirement: Error propagation in API response
The system SHALL include an error object in the API response when an error occurs, with code and recoverable fields, alongside the reply field containing a user-friendly message.

#### Scenario: Error returned in chat response
- **WHEN** a DATA_NOT_FOUND error occurs during tool execution
- **THEN** response includes {"reply": "未找到订单999的记录", "error": {"code": "DATA_NOT_FOUND", "recoverable": true}}

### Requirement: Recoverable errors allow retry
The system SHALL mark errors as recoverable=true when the user can potentially resolve them by rephrasing or retrying, and recoverable=false for systemic failures.

#### Scenario: Recoverable error
- **WHEN** TOOL_LIMIT error occurs
- **THEN** recoverable=true, user can split the request and retry

#### Scenario: Non-recoverable error
- **WHEN** SYS_ERROR occurs
- **THEN** recoverable=false, user should contact support
