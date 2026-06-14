## Purpose

Define the `correlation_id` that uniquely identifies a single Skill execution across the SSE event stream, jsonl audit log, and frontend message state. Enables end-to-end traceability of a Skill-triggered chain of events.

## ADDED Requirements

### Requirement: correlation_id generation
The system SHALL generate a unique `correlation_id` for each Skill execution using the format `skill_exec_<12 hex characters>` (e.g., `skill_exec_a1b2c3d4e5f6`).

#### Scenario: ID generated on skill match
- **WHEN** a skill is matched
- **THEN** SkillObservability generates a new correlation_id (12 random hex chars) and stores it for the duration of execution

#### Scenario: ID is unique per session
- **WHEN** 100 skills execute in a single session
- **THEN** all 100 correlation_ids are unique (collision probability < 10^-12 for 48-bit entropy)

#### Scenario: ID survives across events
- **WHEN** correlation_id="skill_exec_a1b2c3d4e5f6" is generated
- **THEN** all subsequent SSE events (workflow_step, workflow_result, skill_failed) and log entries for the same execution carry this same correlation_id

### Requirement: correlation_id in SSE events
The system SHALL include the `correlation_id` field in every Skill-related SSE event payload.

#### Scenario: skill_matched event
- **WHEN** agent emits skill_matched
- **THEN** payload includes `correlation_id: "skill_exec_..."`

#### Scenario: workflow_step event
- **WHEN** agent emits workflow_step
- **THEN** payload includes `correlation_id: "skill_exec_..."`

#### Scenario: workflow_result event
- **WHEN** agent emits workflow_result
- **THEN** payload includes `correlation_id: "skill_exec_..."`

#### Scenario: skill_failed event
- **WHEN** agent emits skill_failed
- **THEN** payload includes `correlation_id: "skill_exec_..."`

### Requirement: correlation_id in log entries
The system SHALL include the `correlation_id` field in every Skill-related log entry's `data` object.

#### Scenario: skill_matched log entry
- **WHEN** log_skill_matched is called
- **THEN** log entry data includes `correlation_id: "skill_exec_..."`

#### Scenario: workflow_step log entry
- **WHEN** log_workflow_step is called
- **THEN** log entry data includes `correlation_id: "skill_exec_..."` (matches SSE event's correlation_id)

#### Scenario: Log filtering by correlation_id
- **WHEN** user wants to trace a specific Skill execution
- **THEN** they can `grep '"correlation_id": "skill_exec_abc123"' logs/*.jsonl` to retrieve all related events

### Requirement: correlation_id in frontend message state
The system SHALL store the `correlation_id` in the frontend message object so it can be displayed for debugging.

#### Scenario: Message field
- **WHEN** skill_matched SSE event arrives
- **THEN** frontend sets `message.correlationId = data.correlation_id`

#### Scenario: SkillCard footer
- **WHEN** SkillCard renders with correlationId set
- **THEN** card footer shows small monospace text: `🔗 skill_exec_a1b2c3d4e5f6`

#### Scenario: Hover tooltip
- **WHEN** user hovers over correlation_id text
- **THEN** tooltip explains: "Skill 执行追踪 ID，可在日志中按此 ID 检索完整事件链"

### Requirement: correlation_id lifecycle
The correlation_id SHALL be valid for the duration of one Skill execution (from `skill_matched` event to `workflow_result` or `skill_failed` event) and SHALL NOT be reused.

#### Scenario: Single execution lifecycle
- **WHEN** user triggers one skill
- **THEN** correlation_id is active from skill_matched through workflow_result (or skill_failed), then discarded

#### Scenario: New execution gets new ID
- **WHEN** user triggers another skill after the first completes
- **THEN** a new correlation_id is generated (no carry-over from previous execution)

#### Scenario: New execution replaces old message field
- **WHEN** new skill is matched in a new message
- **THEN** the new message gets a new correlationId; old message retains its own (immutable per-message)
