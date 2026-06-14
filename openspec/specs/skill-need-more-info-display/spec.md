## Purpose

Define the rendering of `need_more_info=True` Skill state in the chat interface, where the Skill handler has paused execution and is waiting for the user to provide additional input. This is distinct from regular LLM continuations.

## Requirements

### Requirement: Need more info banner
The system SHALL display a distinctive "💬 Skill 追问中" banner when a Skill transitions to `need_more_info` state, indicating that the user should provide additional information to continue.

#### Scenario: Banner rendering on need_more_info
- **WHEN** message.skillNeedMoreInfo = {name: "query-order-edit-address", prompt: "请告诉我要改成什么新地址？"}
- **THEN** message renders: `<div class="skill-need-more-info-banner"><span class="icon">💬</span><span>Skill query-order-edit-address 追问中：请告诉我要改成什么新地址？</span></div>`

#### Scenario: No banner when not in need_more_info state
- **WHEN** message.skillNeedMoreInfo is undefined
- **THEN** no banner rendered (normal Skill flow continues)

#### Scenario: Replaces info banner
- **WHEN** message transitions from `skillMatched` to `skillNeedMoreInfo`
- **THEN** info banner is hidden; need_more_info banner shown in its place

### Requirement: SkillCard pause state
The system SHALL show the SkillCard in a "paused" visual state when need_more_info is active.

#### Scenario: Paused step indicator
- **WHEN** SkillCard has completed_steps=2 and pending_step="provide_new_address"
- **THEN** SkillCard shows "⏸️ 等待您回复" badge in header

#### Scenario: Step list frozen
- **WHEN** SkillCard is in need_more_info state
- **THEN** completed steps are shown normally; the "next" step is shown with a dashed border and pause icon

### Requirement: Hint input area
The system SHALL display a hint message in the input area to remind the user that the Skill is waiting for their input.

#### Scenario: Input hint
- **WHEN** session has at least one message with skillNeedMoreInfo
- **THEN** input area shows: "请回复 Skill 追问" hint (similar to "请先处理待确认操作" but for Skill pause state)

#### Scenario: Input hint clears
- **WHEN** user submits a reply to the need_more_info prompt
- **THEN** input hint clears on next skill match (or after success/failure)

### Requirement: User reply triggers new skill match
The system SHALL treat the user's next message as a normal skill match attempt (not as a Skill continuation).

#### Scenario: Reply re-triggers skill matching
- **WHEN** user sends "改成北京" after the Skill prompted for new address
- **THEN** `_resolve_skill_fragments()` runs again on the new message; query-order-edit-address matches again

#### Scenario: New skill invocation
- **WHEN** user's reply matches the same skill
- **THEN** new Skill execution begins with fresh `correlation_id`; previous skill's state is "completed" (frozen) in the message list

#### Scenario: Reply to non-Skill chat
- **WHEN** user's reply does not match any skill
- **THEN** existing tool_call path used; no Skill state in conversation

### Requirement: Banner color and icon
The system SHALL style the need_more_info banner with a friendly blue/cyan color (not red, not green) to convey "waiting for you" without alarm.

#### Scenario: Color theme
- **WHEN** banner renders
- **THEN** background is light blue/cyan, icon is 💬 (speech bubble), text is dark blue (not red)

#### Scenario: Distinction from failure
- **WHEN** user sees both need_more_info banner and failure banner
- **THEN** they are visually distinct: need_more_info is calm blue, failure is alarming red