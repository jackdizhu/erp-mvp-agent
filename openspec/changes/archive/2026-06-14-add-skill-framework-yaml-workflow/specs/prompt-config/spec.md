## MODIFIED Requirements

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

## ADDED Requirements

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
