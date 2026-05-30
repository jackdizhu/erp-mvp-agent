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

#### Scenario: Intent rules configurable
- **WHEN** system loads intent rules
- **THEN** rules are loaded from `config.py` or `intent_detector.py` with zh/en patterns for each tool

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

#### Scenario: No intent, normal reply passed through
- **WHEN** user sends "你好" and LLM returns no tool_calls
- **THEN** `detect_tool_intent()` returns None
- **AND** system returns LLM reply directly without retry

### Requirement: Approval flow verification (Node 2)
The system SHALL verify that all DANGER-level tool calls have successfully created pending actions, and reject the response if approval creation failed.

#### Scenario: DANGER tool creates pending action, verification passes
- **WHEN** LLM returns tool_call for update_order (DANGER)
- **THEN** `approval_manager.create_pending()` is called
- **AND** pending_action is returned in response
- **AND** verification passes

#### Scenario: DANGER tool fails to create pending action
- **WHEN** LLM returns tool_call for update_order but `approval_manager.create_pending()` returns None (e.g., max_pending exceeded)
- **THEN** system returns APPROVAL_FAILED error
- **AND** response includes error with code="APPROVAL_FAILED"

#### Scenario: DANGER tools executed but no pending_action returned
- **WHEN** code logic error causes DANGER tool to execute without creating pending_action
- **THEN** system detects has_danger_tools_executed AND not pending_action
- **AND** system returns APPROVAL_REQUIRED error

#### Scenario: SAFE/CAUTION tools skip approval verification
- **WHEN** LLM returns tool_calls for query_order (SAFE) and create_order (CAUTION)
- **THEN** approval verification is skipped
- **AND** tools execute normally

### Requirement: New error codes for validation failures
The system SHALL define new error codes for tool call validation and approval flow failures.

| Code | Message | Recoverable | Source |
|------|---------|-------------|--------|
| APPROVAL_FAILED | 高风险操作审批创建失败，请联系管理员 | False | approval |
| APPROVAL_REQUIRED | 此操作需要审批确认，但审批创建失败 | False | approval |
| LLM_RETRY_EXHAUSTED | AI无法正确使用工具，请换种方式描述 | True | llm |

#### Scenario: APPROVAL_FAILED returned
- **WHEN** `approval_manager.create_pending()` returns None for a DANGER tool
- **THEN** response includes error with code="APPROVAL_FAILED"
- **AND** recoverable=False

#### Scenario: APPROVAL_REQUIRED returned
- **WHEN** DANGER tool was processed but no pending_action was created (logic error)
- **THEN** response includes error with code="APPROVAL_REQUIRED"
- **AND** recoverable=False

#### Scenario: LLM_RETRY_EXHAUSTED returned
- **WHEN** LLM retry after hallucination still returns no tool_calls
- **THEN** response includes error with code="LLM_RETRY_EXHAUSTED"
- **AND** recoverable=True
- **AND** reply suggests user rephrase their request

### Requirement: Intent rule pattern design
The system SHALL use conservative regex patterns that only match clear operation intent, avoiding false positives on normal queries.

#### Scenario: Pattern matches clear operation
- **GIVEN** pattern "修改.*订单"
- **WHEN** message is "帮我修改订单123的地址"
- **THEN** pattern matches, returns update_order

#### Scenario: Pattern does not match normal query
- **GIVEN** pattern "修改.*订单"
- **WHEN** message is "订单123可以修改吗？"
- **THEN** pattern does NOT match (question form, not operation intent)

#### Scenario: English pattern works
- **GIVEN** pattern "update.*order"
- **WHEN** message is "I need to update order 123 address"
- **THEN** pattern matches (case-insensitive), returns update_order

### Requirement: Configurable intent rules
The system SHALL load intent rules from a JSON configuration file, supporting runtime updates without code changes, with environment variable override for file path.

#### Scenario: Default config file loaded
- **WHEN** system starts
- **THEN** `intent_detector.py` loads rules from `app/config/intent_rules.json` by default
- **AND** rules contain zh/en patterns for all DANGER tools

#### Scenario: Custom config path via environment variable
- **WHEN** environment variable `INTENT_RULES_PATH` is set to `/custom/path/rules.json`
- **THEN** system loads rules from the custom path instead of default

#### Scenario: Config file format
- **GIVEN** `intent_rules.json` structure:
```json
{
  "update_order": {
    "zh": ["修改.*订单", "改.*地址", "更新.*订单"],
    "en": ["update.*order", "change.*address"]
  },
  "cancel_order": {
    "zh": ["取消.*订单", "退掉.*订单"],
    "en": ["cancel.*order", "delete.*order"]
  }
}
```
- **WHEN** system loads the file
- **THEN** rules are parsed and cached in memory

#### Scenario: Config validation on load
- **WHEN** config file contains invalid structure (missing zh/en keys)
- **THEN** system logs a warning and falls back to built-in default rules
- **AND** system continues to operate with defaults

#### Scenario: Runtime config reload
- **WHEN** `reload_intent_rules()` is called (e.g., via admin API or file watcher)
- **THEN** system reloads rules from the configured path
- **AND** new rules are applied to subsequent requests

### Requirement: Comprehensive keyword coverage
The system SHALL include a comprehensive set of Chinese and English keywords covering common operation expressions for all DANGER-level tools.

#### Scenario: Chinese keywords for update_order
- **GIVEN** update_order keywords include:
  - "修改.*订单", "改.*地址", "改.*电话", "更新.*订单",
  - "变更.*订单", "订单.*改为", "地址.*改成", "电话.*改成"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "update_order"

#### Scenario: English keywords for update_order
- **GIVEN** update_order keywords include:
  - "update.*order", "change.*address", "modify.*order",
  - "edit.*order", "order.*to", "address.*to", "phone.*to"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "update_order"

#### Scenario: Chinese keywords for cancel_order
- **GIVEN** cancel_order keywords include:
  - "取消.*订单", "不要.*订单", "退掉.*订单", "订单.*取消",
  - "撤销.*订单", "作废.*订单"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "cancel_order"

#### Scenario: English keywords for cancel_order
- **GIVEN** cancel_order keywords include:
  - "cancel.*order", "delete.*order", "remove.*order",
  - "void.*order", "revoke.*order"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "cancel_order"

#### Scenario: Chinese keywords for delete_order
- **GIVEN** delete_order keywords include:
  - "删除.*订单", "删掉.*订单", "移除.*订单", "彻底.*删除"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "delete_order"

#### Scenario: English keywords for delete_order
- **GIVEN** delete_order keywords include:
  - "delete.*order", "remove.*order.*permanently", "purge.*order"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "delete_order"

#### Scenario: Chinese keywords for adjust_inventory
- **GIVEN** adjust_inventory keywords include:
  - "调整.*库存", "修改.*库存", "增加.*库存", "减少.*库存",
  - "库存.*加", "库存.*减", "补货", "入库", "出库"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "adjust_inventory"

#### Scenario: English keywords for adjust_inventory
- **GIVEN** adjust_inventory keywords include:
  - "adjust.*inventory", "update.*stock", "add.*stock",
  - "increase.*inventory", "decrease.*inventory", "restock",
  - "stock.*in", "stock.*out"
- **WHEN** user sends any of these patterns
- **THEN** `detect_tool_intent()` returns "adjust_inventory"

### Requirement: Retry message construction
The system SHALL construct a retry message that guides LLM to use the correct tool, including the expected tool name and the previous incorrect reply.

#### Scenario: Retry message includes tool guidance
- **WHEN** system triggers retry for expected_tool="update_order"
- **THEN** messages appended include:
  - `{"role": "assistant", "content": previous_reply}` (the hallucinated reply)
  - `{"role": "system", "content": "请使用 update_order 工具重新处理此请求。此操作需要调用工具而非直接回答。"}`

#### Scenario: Retry respects token limits
- **WHEN** retry is triggered
- **THEN** retry uses the same messages array (already truncated to N=6)
- **AND** only 2 additional messages are appended
- **AND** total messages stay within token limits
