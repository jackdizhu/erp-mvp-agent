## ADDED Requirements

### Requirement: Skill fragment application logging
The `build_system_prompt` function SHALL record whether `skill_fragments` was applied (non-empty) to the system prompt, exposed via a return value or side-effect for observability.

#### Scenario: Fragments applied
- **WHEN** `build_system_prompt("查询订单时展示：状态、地址")` is called with non-empty fragments
- **THEN** function returns system prompt that includes the "=== 技能指引 ===" section
- **AND** the agent (caller) logs a `skill_fragment_applied` event with the fragment content (audit trail)

#### Scenario: Empty fragments no-op
- **WHEN** `build_system_prompt("")` or `build_system_prompt()` is called
- **THEN** system prompt is identical to no-fragments version; no `skill_fragment_applied` log entry (since fragments were not applied)

#### Scenario: Fragment truncation for log
- **WHEN** fragments are 500 characters and applied
- **THEN** `skill_fragment_applied` log entry contains the first 200 characters + "..." (consistent with other field truncation)

### Requirement: Audit trail for prompt injection
The agent (or `build_system_prompt` wrapper) SHALL emit a log entry whenever Skill fragments are injected, enabling post-hoc audit of "which Skills' guidance was used in this response".

#### Scenario: Log structure
- **WHEN** fragments are applied
- **THEN** log entry has `type: "skill_fragment_applied"`, `data: {skill_name, fragment_preview (200 chars), fragment_length, applied_at: timestamp}`

#### Scenario: Multiple fragments aggregated
- **WHEN** build_system_prompt receives fragments from multiple skills (via `registry.get_prompt_fragments(skill_names)`)
- **THEN** a single `skill_fragment_applied` log entry is written per chat request (aggregated, not one per skill)

#### Scenario: No log for backward compat
- **WHEN** agent does NOT use Skill framework (ENABLE_SKILL=False)
- **THEN** no `skill_fragment_applied` log entries (preserves old behavior)
