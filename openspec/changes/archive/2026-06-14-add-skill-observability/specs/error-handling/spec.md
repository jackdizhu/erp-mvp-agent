## ADDED Requirements

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
