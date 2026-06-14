## ADDED Requirements

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
