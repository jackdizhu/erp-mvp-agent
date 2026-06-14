## Purpose

Define the rendering of Skill execution failures in the chat interface. Reuses the existing `error-message-banner` component but with Skill-specific error context (skill name, error code, original cause).

## ADDED Requirements

### Requirement: Skill failure red banner
The system SHALL display a red error banner (reusing `.error-message-banner` CSS class) when a skill fails, showing the skill name, error code, and a user-friendly message.

#### Scenario: Failure banner rendering
- **WHEN** message.skillFailed = {name: "query-order-edit-address", error_code: "SKILL_EXECUTION_FAILED", error_detail: "无法识别订单号"}
- **THEN** message renders: `<div class="error-message-banner"><span class="error-icon">⚠️</span><span class="error-text">技能 query-order-edit-address 执行失败：无法识别订单号（错误码：SKILL_EXECUTION_FAILED）</span></div>`

#### Scenario: No banner when no failure
- **WHEN** message.skillFailed is undefined or null
- **THEN** no error banner is rendered (existing message flow proceeds)

#### Scenario: Recoverable error
- **WHEN** SKILL_EXECUTION_FAILED with recoverable=true
- **THEN** banner includes hint: "可重试或换种方式描述" at the end

#### Scenario: Error detail truncated
- **WHEN** error_detail is longer than 100 characters
- **THEN** banner message shows first 100 chars + "..." (e.g., "技能 my-skill 执行失败：步骤 batch_query 执行失败: HTTPError 500 Server Err...")

### Requirement: Failure banner interaction with SkillCard
The system SHALL display the failure banner ABOVE the SkillCard (if present) and ensure both are visible for context.

#### Scenario: Failure with SkillCard
- **WHEN** message has both `skillMatched` and `skillFailed` fields
- **THEN** error banner is rendered first (top), SkillCard rendered below

#### Scenario: Failure with failed_step_id
- **WHEN** skillFailed has `failed_step_id: "batch_query"`
- **THEN** SkillCard's matching step row is highlighted (red border) to indicate which step caused the failure

### Requirement: Click banner to expand SkillCard
The system SHALL make the failure banner clickable to expand the SkillCard and show the failed step details.

#### Scenario: Banner click behavior
- **WHEN** user clicks the failure banner
- **THEN** SkillCard (if present) expands and scrolls to the failed step

#### Scenario: Banner without SkillCard
- **WHEN** user clicks failure banner but no SkillCard is present
- **THEN** no-op (no error)

### Requirement: Failure during streaming
The system SHALL display the failure banner immediately when `skill_failed` SSE event arrives, even before the `done` event.

#### Scenario: Mid-stream failure
- **WHEN** user triggers a skill that fails after 1 second
- **THEN** failure banner appears at 1s mark (before done at 1.2s)
- **AND** streaming state transitions to "done" with error code

#### Scenario: Stream abort on failure
- **WHEN** failure occurs
- **THEN** no further `reply_chunk` events for this Skill (no incomplete reply)

### Requirement: Distinct from tool error
The system SHALL distinguish Skill errors from tool errors visually: Skill error banner is wider and includes the skill name, while tool errors are per-tool inline.

#### Scenario: Side-by-side comparison
- **WHEN** user sees both a failed tool (query_order returning 500) and a failed skill
- **THEN** tool error appears as inline red text in tool card; skill error appears as full-width banner above
