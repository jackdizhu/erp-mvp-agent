## ADDED Requirements

### Requirement: Chat endpoint accepts message with history
The system SHALL provide a POST /chat endpoint that accepts a JSON body containing `message` (string) and `history` (array of {role, content} objects), and returns a JSON response containing `reply` (string).

#### Scenario: Simple query without history
- **WHEN** client sends POST /chat with message="查询订单123状态" and empty history
- **THEN** system returns JSON with reply field containing the agent's response

#### Scenario: Query with conversation history
- **WHEN** client sends POST /chat with message="帮我改一下收货地址" and history containing previous messages about order 123
- **THEN** system uses history context to understand "一下" refers to order 123

### Requirement: Chat response includes tool calls transparency
The system SHALL include a `tool_calls` array in the chat response, listing each tool call made during the request with its tool name, arguments, and result.

#### Scenario: Tool call returned in response
- **WHEN** agent executes query_order("123") to answer a user question
- **THEN** response includes tool_calls: [{tool: "query_order", args: {order_id: "123"}, result: {...}}]

### Requirement: Chat response includes pending action for DANGER tools
The system SHALL include a `pending_action` object in the chat response when a DANGER-level tool is invoked, containing id, tool, args, risk_level, summary, and detail fields.

#### Scenario: DANGER tool returns pending action
- **WHEN** agent determines update_order is needed
- **THEN** response includes pending_action with id, tool="update_order", risk_level="DANGER", and a human-readable summary

### Requirement: Confirm endpoint executes or rejects pending actions
The system SHALL provide a POST /chat/confirm endpoint that accepts `action_id` (string), `approved` (boolean), and `history` (array), and returns the execution result or cancellation message.

#### Scenario: Approved action executes successfully
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123" and approved=true
- **THEN** system executes the pending tool call and returns the result

#### Scenario: Rejected action returns cancellation message
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123" and approved=false
- **THEN** system returns reply="操作已取消" and clears the pending action

#### Scenario: Expired action returns error
- **WHEN** client sends POST /chat/confirm with an expired action_id
- **THEN** system returns error with code TOOL_EXPIRED and message="操作已过期，请重新发起"

### Requirement: History window truncation
The system SHALL truncate the history array to the most recent N=6 messages before sending to LLM, where N is configurable via config.py.

#### Scenario: History exceeds window size
- **WHEN** client sends 10 messages in history
- **THEN** system only sends the most recent 6 messages to the LLM
