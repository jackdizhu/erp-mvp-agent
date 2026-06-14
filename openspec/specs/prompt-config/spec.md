# Prompt Configuration

## Purpose

Provide centralized, configurable system prompt management for the ERP agent. This enables runtime customization of prompts without code changes and supports dynamic capability enumeration from tool schemas.

## Requirements

### Requirement: YAML Configuration Loading
The system SHALL load prompt configuration from `app/config/prompts.yaml` file.

#### Scenario: Load valid YAML configuration
- **WHEN** system starts with valid `prompts.yaml` file
- **THEN** configuration SHALL be parsed successfully
- **AND** `load_prompts()` SHALL return dictionary with keys: role, risk_notice, response_style, capabilities_header

#### Scenario: Fallback on missing configuration
- **WHEN** `prompts.yaml` file does not exist
- **THEN** system SHALL use hardcoded fallback values
- **AND** system SHALL log warning message

#### Scenario: Fallback on invalid YAML
- **WHEN** `prompts.yaml` file exists but contains invalid YAML
- **THEN** system SHALL use hardcoded fallback values
- **AND** system SHALL log error message with parsing details

### Requirement: Dynamic Capability List Generation
The system SHALL generate capability list automatically from `erp_app/tools.py` TOOL_SCHEMAS.

#### Scenario: Generate capabilities from tool schemas
- **WHEN** `build_system_prompt()` is called
- **THEN** system SHALL extract all tool descriptions from TOOL_SCHEMAS
- **AND** format each as "- {description}" bullet point

#### Scenario: Empty tools list handling
- **WHEN** TOOL_SCHEMAS is empty
- **THEN** capability list SHALL be empty string
- **AND** system SHALL continue without error

### Requirement: System Prompt Assembly
The system SHALL assemble complete system prompt from configuration, dynamic content, and optional skill fragments passed as parameter.

#### Scenario: Assemble complete prompt without skill fragments
- **WHEN** `build_system_prompt()` is called with no arguments
- **THEN** output SHALL follow structure:
```
{role}

{capabilities_header}
- {tool_description_1}
- {tool_description_2}
...

{risk_notice}
{response_style}
```
- **AND** the output is byte-for-byte equivalent to the previous default (no regression)

#### Scenario: Assemble prompt with skill fragments
- **WHEN** `build_system_prompt(skill_fragments="查询订单时展示：状态、地址、送达时间")` is called
- **THEN** output SHALL follow structure:
```
{role}

{capabilities_header}
- {tool_description_1}
- {tool_description_2}
...

{risk_notice}
{response_style}


=== 技能指引 ===
查询订单时展示：状态、地址、送达时间
```
- **AND** the "=== 技能指引 ===" section is appended at the end, separated from response_style by a blank line

#### Scenario: Exclude empty optional sections
- **WHEN** capabilities_footer is empty or not configured
- **THEN** system SHALL skip that section in final output

#### Scenario: Empty skill fragments skip skill section
- **WHEN** `build_system_prompt(skill_fragments="")` is called
- **THEN** output does NOT contain the "=== 技能指引 ===" section
- **AND** the output is equivalent to `build_system_prompt()` with no args

### Requirement: Dynamic system prompt per chat request
The system SHALL call `build_system_prompt(skill_fragments)` per chat request in `app/agent.py:build_messages()` rather than using a module-level cached constant. The function signature changes from `build_system_prompt() -> str` to `build_system_prompt(skill_fragments: str = "") -> str`.

#### Scenario: Module-level constant removed
- **WHEN** `app/llm.py` is inspected
- **THEN** no module-level variable named `SYSTEM_PROMPT` exists
- **AND** `app/agent.py` does not import `SYSTEM_PROMPT` from `app.llm`

#### Scenario: Per-request invocation
- **WHEN** two chat requests have different matched skills with different prompt_fragments
- **THEN** each request produces a distinct system prompt (no shared cached value)

#### Scenario: Backward-compatible default
- **WHEN** no skill is matched
- **THEN** `build_messages` calls `build_system_prompt()` with no args
- **AND** existing /chat behavior is unchanged from the previous version (no regression for non-skill requests)

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

### Requirement: Prompt Configuration Structure
The YAML configuration SHALL support the following structure:

```yaml
system_prompt:
  role: "你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。"
  capabilities_header: "你可以执行以下操作："
  capabilities_footer: ""  # optional
  risk_notice: "对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。"
  response_style: "请用简洁专业的中文回复用户。"
```

#### Scenario: Load all configuration fields
- **WHEN** `prompts.yaml` contains all defined fields
- **THEN** `load_prompts()` SHALL return all values correctly parsed

#### Scenario: Support missing optional fields
- **WHEN** `prompts.yaml` is missing capabilities_footer
- **THEN** system SHALL use empty string as default value
- **AND** system SHALL NOT raise error