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

### Requirement: Skill layer error code
The system SHALL define error code `SKILL_EXECUTION_FAILED` with `source="skill"` and `recoverable=true`, used when a matched skill's executor returns `WorkflowResult(success=False)` or raises an exception.

#### Scenario: Handler exception caught
- **WHEN** SkillHandler.execute() raises an exception during skill execution
- **THEN** agent returns AgentError with code="SKILL_EXECUTION_FAILED", message includes skill name and error detail, source="skill", recoverable=true

#### Scenario: YAML workflow step failure
- **WHEN** a tool_call step in YAML workflow fails (client_factory.execute_tool raises)
- **THEN** agent returns AgentError with code="SKILL_EXECUTION_FAILED", message="技能 'xxx' 执行失败：步骤 'X' 执行失败: <reason>", source="skill", recoverable=true

#### Scenario: User-facing message
- **WHEN** SKILL_EXECUTION_FAILED is returned to the frontend
- **THEN** the `reply` field contains a user-friendly Chinese message such as "技能 query-order-search 执行失败：xxx，请稍后重试或换种方式描述"
- **AND** the `error` object contains `{code: "SKILL_EXECUTION_FAILED", recoverable: true}`

#### Scenario: Non-fallback semantics
- **WHEN** SKILL_EXECUTION_FAILED is returned
- **THEN** the agent does NOT retry the LLM call, does NOT call detect_tool_intent, does NOT create a pending action
- **AND** the error is the terminal response for the current chat request

### Requirement: Skill error message format
The system SHALL format the SKILL_EXECUTION_FAILED message as: `"技能 <skill_name> 执行失败：<error_detail>"` where `<skill_name>` is the matched skill's name and `<error_detail>` is from `WorkflowResult.error` or the exception's string representation.

#### Scenario: Message includes skill name
- **WHEN** matched skill is "query-order-edit-address" and handler fails with "无法识别订单号"
- **THEN** AgentError.message = "技能 query-order-edit-address 执行失败：无法识别订单号"

#### Scenario: Message truncation for long errors
- **WHEN** WorkflowResult.error is longer than 200 chars
- **THEN** AgentError.message truncates the error_detail to 200 chars + "..."

### Requirement: SKILL_EXECUTION_FAILED frontend rendering
The system SHALL render `SKILL_EXECUTION_FAILED` errors in the chat interface via the red `error-message-banner` style, with the skill name, error code, and user-friendly message.

#### Scenario: Error in API response
- **WHEN** `/chat` returns error `{code: "SKILL_EXECUTION_FAILED", message: "技能 query-order-search 执行失败：xxx", recoverable: true}`
- **THEN** chat response includes `reply: "技能 query-order-search 执行失败：xxx"` and `error: {code: "SKILL_EXECUTION_FAILED", recoverable: true}`

#### Scenario: Error in SSE stream
- **WHEN** `/chat/stream` emits `event: done` with `error: {code: "SKILL_EXECUTION_FAILED", message: "...", recoverable: true}`
- **THEN** frontend shows red error banner: "技能 query-order-search 执行失败：xxx" with "可重试或换种方式描述" hint

#### Scenario: Distinct from tool error
- **WHEN** chat response has BOTH a failed tool (TOOL_NOT_FOUND) and a failed skill (SKILL_EXECUTION_FAILED)
- **THEN** tool error appears as inline text in tool card; skill error appears as full-width banner (mutually exclusive display paths)

### Requirement: Recoverability hint for skill errors
The frontend SHALL display a "可重试" hint for recoverable Skill errors and a "需联系管理员" hint for non-recoverable ones.

#### Scenario: Recoverable=true
- **WHEN** error.recoverable=true (default for SKILL_EXECUTION_FAILED)
- **THEN** banner message ends with "（可重试或换种方式描述）"

#### Scenario: Non-recoverable
- **WHEN** error.recoverable=false (e.g., APPROVAL_FAILED)
- **THEN** banner message ends with "（需联系管理员）"

### Requirement: Skill error code visibility
The frontend SHALL display the error code in parentheses after the main error message for technical debugging.

#### Scenario: Code shown
- **WHEN** error.code = "SKILL_EXECUTION_FAILED"
- **THEN** banner message shows: "技能 query-order-search 执行失败：xxx（错误码：SKILL_EXECUTION_FAILED）"

#### Scenario: Code truncation
- **WHEN** error.message is longer than 100 characters
- **THEN** main message is truncated to 100 chars + "..."; error code is shown in full after
