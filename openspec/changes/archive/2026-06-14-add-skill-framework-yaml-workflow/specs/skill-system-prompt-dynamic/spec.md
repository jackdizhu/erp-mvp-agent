## Purpose

Define dynamic System Prompt injection: the module-level `SYSTEM_PROMPT` constant in `app/llm.py` is removed; `build_system_prompt(skill_fragments)` is called per chat request from `agent.py` to inject the matched skill's prompt_fragment into the system prompt.

## ADDED Requirements

### Requirement: Remove module-level SYSTEM_PROMPT
The system SHALL remove the `SYSTEM_PROMPT = build_system_prompt()` line from `app/llm.py` and the corresponding import in `app/agent.py` (`from app.llm import SYSTEM_PROMPT`).

#### Scenario: Constant removed
- **WHEN** `app/llm.py` is inspected
- **THEN** no module-level variable named `SYSTEM_PROMPT` exists

#### Scenario: agent.py import removed
- **WHEN** `app/agent.py` is inspected
- **THEN** line `from app.llm import SYSTEM_PROMPT` is absent

### Requirement: build_system_prompt accepts skill_fragments parameter
The system SHALL change `build_system_prompt()` signature to `build_system_prompt(skill_fragments: str = "") -> str`, and append a "=== 技能指引 ===" section containing skill_fragments when non-empty.

#### Scenario: Default empty
- **WHEN** `build_system_prompt()` is called with no args
- **THEN** output is identical to current behavior (no skill section)

#### Scenario: Fragments appended
- **WHEN** `build_system_prompt("查询订单时展示：状态、地址、送达时间")` is called
- **THEN** output contains section: "=== 技能指引 ===\n查询订单时展示：状态、地址、送达时间"

#### Scenario: Empty fragments skip section
- **WHEN** `build_system_prompt("")` is called
- **THEN** output does not contain "=== 技能指引 ===" section

### Requirement: agent.py calls build_system_prompt per request
The system SHALL modify `build_messages()` in `app/agent.py` to accept `skill_fragments: str` parameter and call `build_system_prompt(skill_fragments)` instead of using a cached constant.

#### Scenario: No skill matched
- **WHEN** user message does not match any skill
- **THEN** build_messages is called with skill_fragments="", system prompt is unchanged from current behavior

#### Scenario: Skill matched
- **WHEN** user message matches query-order-search skill
- **THEN** build_messages is called with skill_fragments=query-order-search.prompt_fragment, system prompt contains the fragment

#### Scenario: Stream chat also uses dynamic prompt
- **WHEN** stream_chat() is called
- **THEN** same build_messages with skill_fragments is used (not a separate constant)

### Requirement: LLM call site remains tools-parameterized
The system SHALL keep the fix that `call_llm(messages, tools)` uses the passed-in `tools` argument instead of hardcoded `get_openai_tools()` (already required by design, preserved during refactor).

#### Scenario: Tools passed correctly
- **WHEN** agent calls call_llm with messages and client_factory.get_all_tools()
- **THEN** kwargs["tools"] equals the passed tools (not get_openai_tools() result)

#### Scenario: Stream tools passed correctly
- **WHEN** agent calls call_llm_stream with messages and tools
- **THEN** kwargs["tools"] equals the passed tools

### Requirement: No caching of skill-specific prompts
The system SHALL NOT cache the result of `build_system_prompt(skill_fragments=X)` in any module-level variable; each chat request recomputes.

#### Scenario: Per-request computation
- **WHEN** two chat requests have different skill_fragments
- **THEN** each request produces a different system_prompt string (no shared cached value)

#### Scenario: Performance acceptable
- **WHEN** build_system_prompt is called per request
- **THEN** wall-clock overhead per chat request is < 1ms (string concatenation only, no IO)
