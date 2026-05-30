## Purpose

Define the tool call validation mechanism, intent detection engine, and approval flow verification to prevent LLM hallucination from bypassing tool execution and DANGER-level approval requirements.

## Requirements

### Requirement: Intent detection engine
The system SHALL provide an intent detection engine that analyzes user messages using regex patterns to determine if a tool call is expected, supporting both Chinese and English input.

#### Scenario: Chinese intent detected for update_order
- **WHEN** user sends "把订单123的地址改成北京市朝阳区"
- **THEN** `detect_tool_intent()` returns "update_order"

#### Scenario: English intent detected for cancel_order
- **WHEN** user sends "Please cancel order 124"
- **THEN** `detect_tool_intent()` returns "cancel_order"

#### Scenario: No intent for normal query
- **WHEN** user sends "订单123现在什么状态？"
- **THEN** `detect_tool_intent()` returns None

### Requirement: Tool call validation (Node 1)
The system SHALL validate whether LLM actually returned tool_calls when intent detection indicates a tool is needed, and force a retry if LLM hallucinated.

#### Scenario: LLM returns tool_calls, validation passes
- **WHEN** user sends "修改订单123地址" and LLM returns tool_calls for update_order
- **THEN** validation passes, tool calls are executed normally

#### Scenario: LLM hallucination detected, retry triggered
- **WHEN** user sends "修改订单123地址" but LLM returns finish_reason=stop with content="地址已修改"
- **THEN** system detects hallucination via intent detection
- **AND** system appends a retry message to messages
- **AND** system calls LLM again with tool schemas
- **AND** if retry returns tool_calls, they are executed normally

#### Scenario: LLM retry still fails
- **WHEN** user sends operation-intent message but LLM retry still returns no tool_calls
- **THEN** system returns LLM_RETRY_EXHAUSTED error with user-friendly message

### Requirement: Approval flow verification (Node 2)
The system SHALL verify that all DANGER-level tool calls have successfully created pending actions, and reject the response if approval creation failed.

#### Scenario: DANGER tool creates pending action, verification passes
- **WHEN** LLM returns tool_call for update_order (DANGER)
- **THEN** `approval_manager.create_pending()` is called
- **AND** pending_action is returned in response

#### Scenario: DANGER tool fails to create pending action
- **WHEN** LLM returns tool_call for update_order but `approval_manager.create_pending()` returns None (e.g., max_pending exceeded)
- **THEN** system returns APPROVAL_FAILED error

#### Scenario: DANGER tools executed but no pending_action returned
- **WHEN** code logic error causes DANGER tool to execute without creating pending_action
- **THEN** system detects has_danger_tools_executed AND not pending_action
- **AND** system returns APPROVAL_REQUIRED error

### Requirement: Configurable intent rules
The system SHALL load intent rules from a JSON configuration file, supporting runtime updates without code changes, with environment variable override for file path.

#### Scenario: Default config file loaded
- **WHEN** system starts
- **THEN** `intent_detector.py` loads rules from `app/config/intent_rules.json` by default

#### Scenario: Custom config path via environment variable
- **WHEN** environment variable `INTENT_RULES_PATH` is set to `/custom/path/rules.json`
- **THEN** system loads rules from the custom path instead of default

#### Scenario: Config validation on load
- **WHEN** config file contains invalid structure (missing zh/en keys)
- **THEN** system logs a warning and falls back to built-in default rules

#### Scenario: Runtime config reload
- **WHEN** `reload_intent_rules()` is called
- **THEN** system reloads rules from the configured path
