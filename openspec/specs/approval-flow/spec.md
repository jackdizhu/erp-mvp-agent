## Purpose

Define the pending action lifecycle including creation, TTL expiration, confirmation, and cleanup for DANGER-level tool operations.

## Requirements

### Requirement: Pending action creation for DANGER tools
The system SHALL create a pending action with a unique ID, store the tool name, args, LLM messages context, and creation timestamp in memory when a DANGER-level tool is invoked.

#### Scenario: DANGER tool creates pending action
- **WHEN** agent encounters a DANGER-level tool call for update_order
- **THEN** system generates unique action_id, stores tool/args/messages_context/created_at, and returns pending_action to frontend

### Requirement: Pending action TTL expiration
The system SHALL set a TTL of 300 seconds (5 minutes, configurable) on each pending action, after which the action expires and cannot be confirmed.

#### Scenario: Action confirmed within TTL
- **WHEN** user confirms action within 5 minutes
- **THEN** system executes the tool normally

#### Scenario: Action confirmed after TTL
- **WHEN** user confirms action after 5 minutes
- **THEN** system returns TOOL_EXPIRED error and clears the pending action

### Requirement: Pending action confirmation
The system SHALL execute the stored tool call when confirm(action_id, approved=True) is called, and clear the stored data when approved=False.

#### Scenario: Confirm executes tool
- **WHEN** confirm("act_abc123", approved=True) is called
- **THEN** system retrieves stored tool call, executes it, sends result to LLM, and returns final reply

#### Scenario: Reject clears action
- **WHEN** confirm("act_abc123", approved=False) is called
- **THEN** system clears the pending action and returns "操作已取消"

### Requirement: Multiple pending actions managed independently
The system SHALL support multiple pending actions simultaneously, each with its own action_id, and each confirmed or rejected independently.

#### Scenario: Two DANGER tools create two pending actions
- **WHEN** LLM returns tool_calls for update_order and cancel_order
- **THEN** system creates two separate pending actions with different IDs, frontend displays two independent approval cards

#### Scenario: Confirm one action does not affect the other
- **WHEN** user confirms action 1 but rejects action 2
- **THEN** action 1 executes, action 2 is cancelled, both results are reflected independently

### Requirement: Action summary generation
The system SHALL generate a human-readable summary for each pending action using ACTION_SUMMARIES templates from config.py, filling in args values.

#### Scenario: Update order summary
- **WHEN** pending action for update_order(order_id="123", field="address", value="北京") is created
- **THEN** summary is "修改订单123的收货地址"

### Requirement: Action detail for approval card
The system SHALL generate a detail object for each pending action containing action_type, fields array (name-value pairs), and irreversible flag, for frontend approval card rendering.

#### Scenario: Delete order detail
- **WHEN** pending action for delete_order(order_id="125") is created
- **THEN** detail includes action_type="delete_order", fields=[{name:"订单编号",value:"125"},{name:"当前状态",value:"已取消"}], irreversible=true

### Requirement: Expired actions cleanup
The system SHALL clean up expired pending actions on each new request to prevent memory leaks, with max_pending=10 limit.

#### Scenario: Cleanup on new request
- **WHEN** a new chat request arrives and pending actions contain expired entries
- **THEN** system removes all expired entries before processing
