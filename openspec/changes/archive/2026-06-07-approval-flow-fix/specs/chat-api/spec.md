## ADDED Requirements

### Requirement: Approval create endpoint
The system SHALL provide POST /api/approval/create endpoint that validates an approval action and returns whether it is supported, along with display metadata for the approval card.

#### Scenario: Create approval for valid action
- **WHEN** client sends POST /api/approval/create with action_id="act_abc123", tool="update_order", args={...}
- **THEN** system validates via approval_store, returns {supported: true, action_id: "act_abc123", fields: [...], irreversible: false, warning: null}

#### Scenario: Create approval for invalid action
- **WHEN** client sends POST /api/approval/create with action_id="act_unknown"
- **THEN** system returns {supported: false, action_id: "act_unknown", reason: "ACTION_NOT_FOUND"}

### Requirement: Approval decide endpoint
The system SHALL provide POST /api/approval/decide endpoint that records the user's approval decision and generates a user_op_id.

#### Scenario: User approves action
- **WHEN** client sends POST /api/approval/decide with action_id="act_abc123", approved=true
- **THEN** system generates user_op_id, returns {user_op_id: "uop_xxxxxxxxxxxx", action_id: "act_abc123", approved: true, status: "approved"}

#### Scenario: User rejects action
- **WHEN** client sends POST /api/approval/decide with action_id="act_abc123", approved=false
- **THEN** system generates user_op_id, returns {user_op_id: "uop_xxxxxxxxxxxx", action_id: "act_abc123", approved: false, status: "rejected"}

#### Scenario: Decide on invalid action returns 400
- **WHEN** client sends POST /api/approval/decide with action_id not found or already decided
- **THEN** system returns HTTP 400 with error detail

## MODIFIED Requirements

### Requirement: Confirm endpoint executes or rejects pending actions
The system SHALL provide a POST /chat/confirm endpoint that accepts `action_id` (string), `approved` (boolean), `history` (array), and optional `user_op_id` (string), and returns the execution result or cancellation message. When `user_op_id` is provided, the system SHALL pass it to `confirm_action` for preapproved execution.

#### Scenario: Approved action executes successfully with user_op_id
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123", approved=true, user_op_id="uop_xxxxxxxxxxxx"
- **THEN** system executes the pending tool call with preapproved flag and returns the result

#### Scenario: Approved action executes successfully without user_op_id
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123", approved=true (no user_op_id)
- **THEN** system executes the pending tool call normally (backward compatible)

#### Scenario: Rejected action returns cancellation message
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123" and approved=false
- **THEN** system returns reply="操作已取消" and clears the pending action

#### Scenario: Expired action returns error
- **WHEN** client sends POST /chat/confirm with an expired action_id
- **THEN** system returns error with code TOOL_EXPIRED and message="操作已过期，请重新发起"
