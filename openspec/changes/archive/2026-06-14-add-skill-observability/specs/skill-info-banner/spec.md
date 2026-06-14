## Purpose

Define the Skill match info banner displayed in the chat message area, providing at-a-glance Skill identification independent of the collapsible step list. Distinguishes Skill-driven responses from regular LLM replies.

## ADDED Requirements

### Requirement: Skill match banner
The system SHALL display a banner above the assistant message content when a skill is matched, showing the skill name, category, and available tools.

#### Scenario: Banner rendering
- **WHEN** message.skillMatched = {name: "query-order-search", category: "preset", tools: ["query_order"]}
- **THEN** message renders a banner with: `🎯 已匹配 Skill: query-order-search` + small badge "preset" + tools chips

#### Scenario: No banner when no skill matched
- **WHEN** message.skillMatched is undefined or null
- **THEN** no banner is rendered (existing message styling preserved)

#### Scenario: Banner during streaming
- **WHEN** user sends a message and skill is matched before LLM response
- **THEN** banner appears immediately (not waiting for `done` event) for instant feedback

#### Scenario: Banner persists after done
- **WHEN** streaming completes
- **THEN** banner remains visible (not removed) so user can identify which Skill produced the response

### Requirement: Banner layout and styling
The system SHALL style the banner with a subtle background color and padding to distinguish it from regular message content.

#### Scenario: Visual style
- **WHEN** banner renders
- **THEN** banner has: light purple/indigo background, 8px vertical padding, 12px horizontal padding, slight rounded corners, 1px bottom border for separation

#### Scenario: Tool chips
- **WHEN** skill has tools=["query_order", "update_order"]
- **THEN** banner renders two chips: `🔧 query_order` and `🔧 update_order` (small monospace font, gray background)

#### Scenario: Many tools truncate
- **WHEN** skill has 5+ tools
- **THEN** banner shows first 3 chips + `+N more` indicator (e.g., "+2 more")

### Requirement: Banner click behavior
The system SHALL make the banner clickable to expand the corresponding SkillCard (if present).

#### Scenario: Click expands SkillCard
- **WHEN** user clicks the banner
- **THEN** SkillCard body expands (same behavior as direct SkillCard header click)

#### Scenario: Banner without SkillCard
- **WHEN** banner is present but SkillCard was collapsed/hidden
- **THEN** clicking banner toggles the SkillCard visibility

### Requirement: Mutual exclusion with other state banners
The system SHALL display only ONE of the following at a time: info banner / need_more_info banner / failure banner. They are mutually exclusive by Skill lifecycle.

#### Scenario: Info banner shown
- **WHEN** Skill is matched and executing
- **THEN** info banner shown; need_more_info banner and failure banner hidden

#### Scenario: Need more info banner replaces info banner
- **WHEN** Skill transitions to need_more_info state
- **THEN** info banner replaced by need_more_info banner ("💬 Skill 追问中")

#### Scenario: Failure banner replaces info banner
- **WHEN** Skill execution fails
- **THEN** info banner replaced by failure banner (red error-message-banner)
