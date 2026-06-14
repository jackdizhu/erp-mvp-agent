## Purpose

Define the `SkillCard` React component that displays Skill match information and workflow step progress in the chat interface. Mirrors the collapsible interaction pattern of the existing `ToolStatusCard` but is dedicated to Skill-level metadata.

## Requirements

### Requirement: SkillCard component
The system SHALL provide a `<SkillCard />` React component that renders Skill match information with a collapsible step list.

#### Scenario: Card header
- **WHEN** SkillCard renders with skill_name="query-order-search", category="preset", tools=["query_order"]
- **THEN** header shows: `🎯 Skill: query-order-search [preset]` + status badge + expand arrow

#### Scenario: Collapsed by default
- **WHEN** SkillCard is first rendered (no prior user interaction)
- **THEN** step list body is hidden (default `expanded=false`)

#### Scenario: Click to expand
- **WHEN** user clicks the card header
- **THEN** step list body becomes visible (expanded=true) and arrow rotates ▼

#### Scenario: Click to collapse
- **WHEN** user clicks the header while expanded
- **THEN** step list body hides (expanded=false) and arrow reverts to ▶

### Requirement: Workflow step list rendering
The system SHALL render workflow steps in the order they were executed, with status indicators.

#### Scenario: Step item rendering
- **WHEN** SkillCard receives workflow_steps=[{step_id: "parse_input", type: "prompt", status: "completed"}, {step_id: "batch_query", type: "tool_call", tool: "query_order", status: "completed"}]
- **THEN** each step renders as a row with: `step_id` (bold), `type` badge (prompt/tool_call), `tool` (if present), `status` icon (✅/❌/⏸️)

#### Scenario: Step progress header
- **WHEN** SkillCard has 3 total steps and 2 completed
- **THEN** card header shows "2/3 步已完成" (visible without expanding)

#### Scenario: Empty step list
- **WHEN** SkillCard receives workflow_steps=[]
- **THEN** step body shows "无工作流步骤" placeholder

### Requirement: SkillCard props interface
The system SHALL define `SkillCard` props: `skill_name: string`, `category: string`, `description: string`, `tools: string[]`, `workflow_steps: StepEvent[]`, `correlation_id: string`.

#### Scenario: StepEvent type
- **WHEN** StepEvent is `{ step_id: string, type: "tool_call"|"prompt", tool?: string, instruction?: string, status: "completed"|"failed"|"pending_approval", result_summary?: string }`
- **THEN** TypeScript types compile without error

#### Scenario: Optional correlation_id
- **WHEN** SkillCard receives correlation_id="skill_exec_abc"
- **THEN** correlation_id is shown in footer (small monospace text) for debugging; if absent, footer omitted

### Requirement: Visual distinction from ToolStatusCard
SkillCard SHALL use distinct CSS classes (`.skill-card` not `.tool-status-card`) and a different color theme to avoid confusion with LLM-driven tool calls.

#### Scenario: Color theme
- **WHEN** SkillCard renders
- **THEN** header background is purple/indigo (vs ToolStatusCard's gray/blue); status badge uses purple for pending_approval

#### Scenario: Icon differentiation
- **WHEN** SkillCard renders
- **THEN** header icon is `🎯` (target, for Skill match) vs ToolStatusCard's `⚙️` (gear, for tool call)

### Requirement: Failure state rendering
The system SHALL display a failed SkillCard with red status indicator and folded state (not expanded) for quick visual identification.

#### Scenario: Failed skill card
- **WHEN** SkillCard receives skill_name="my-skill" with status="failed"
- **THEN** header shows red status badge "失败" and the card is NOT expanded by default (click to see error)

#### Scenario: Failure reason
- **WHEN** user expands a failed SkillCard
- **THEN** error_message is shown at top of body (above step list)