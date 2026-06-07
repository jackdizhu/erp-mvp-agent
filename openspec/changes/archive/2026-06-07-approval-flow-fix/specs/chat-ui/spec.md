## ADDED Requirements

### Requirement: Approval card unsupported state
The system SHALL render the ApprovalCard in an unsupported state when approvalMeta.supported is false, hiding confirm/cancel buttons and displaying the reason.

#### Scenario: Unsupported approval card
- **WHEN** ApprovalCard receives approvalMeta with supported=false and reason="ORDER_NOT_FOUND"
- **THEN** card displays "不支持: ORDER_NOT_FOUND" status, no confirm/cancel buttons are rendered

#### Scenario: Supported approval card with buttons
- **WHEN** ApprovalCard receives approvalMeta with supported=true
- **THEN** card displays confirm and cancel buttons as normal

### Requirement: Two-stage approval confirmation flow
The system SHALL implement a two-stage handleConfirm flow: first call approvalDecide to obtain user_op_id, then call chatConfirmWithUserOp with the user_op_id to execute the tool.

#### Scenario: Successful two-stage confirmation
- **WHEN** user clicks confirm on an approval card
- **THEN** system calls approvalDecide(actionId, true, sessionId), receives user_op_id, then calls chatConfirmWithUserOp(sessionId, actionId, true, history, user_op_id)

#### Scenario: Successful two-stage rejection
- **WHEN** user clicks cancel on an approval card
- **THEN** system calls approvalDecide(actionId, false, sessionId), receives user_op_id, then calls chatConfirmWithUserOp(sessionId, actionId, false, history, user_op_id)

#### Scenario: Decide API failure
- **WHEN** approvalDecide returns an error (no user_op_id)
- **THEN** system updates approval card state to "failed" and displays error

#### Scenario: Confirm API failure after decide
- **WHEN** chatConfirmWithUserOp returns an error
- **THEN** system updates approval card state to "failed"

### Requirement: Approval HTTP utility functions
The system SHALL provide approvalCreate, approvalDecide, and chatConfirmWithUserOp functions in httpUtils.js.

#### Scenario: approvalCreate API call
- **WHEN** approvalCreate("act_abc123", "update_order", {order_id: "123"}, "sess_1") is called
- **THEN** sends POST to /api/approval/create with body {action_id: "act_abc123", tool: "update_order", args: {order_id: "123"}, session_id: "sess_1"}

#### Scenario: approvalDecide API call
- **WHEN** approvalDecide("act_abc123", true, "sess_1") is called
- **THEN** sends POST to /api/approval/decide with body {action_id: "act_abc123", approved: true, session_id: "sess_1"}

#### Scenario: chatConfirmWithUserOp API call
- **WHEN** chatConfirmWithUserOp("sess_1", "act_abc123", true, history, "uop_xxxxxxxxxxxx") is called
- **THEN** sends POST to /chat/confirm with body {session_id: "sess_1", action_id: "act_abc123", approved: true, history, user_op_id: "uop_xxxxxxxxxxxx"}

## MODIFIED Requirements

### Requirement: Approval card state transitions
The system SHALL visually update approval cards through states: PENDING (red border, buttons visible), CONFIRMED/EXECUTING (yellow, "执行中..."), SUCCESS (green, result shown), FAILED (red, error shown), REJECTED (gray, "已取消"), EXPIRED (gray, "已过期"), UNSUPPORTED (gray, "不支持" reason shown, no buttons).

#### Scenario: Card transitions from pending to success
- **WHEN** user confirms a card and execution succeeds
- **THEN** card border turns green, buttons disappear, result is displayed

#### Scenario: Card transitions from pending to rejected
- **WHEN** user cancels a card
- **THEN** card border turns gray, buttons disappear, "已取消" is displayed

#### Scenario: Card shows expired state
- **WHEN** a pending card's TTL has expired
- **THEN** card border turns gray, buttons are disabled, "已过期" is displayed

#### Scenario: Card shows unsupported state
- **WHEN** approvalMeta.supported is false
- **THEN** card border turns gray, no buttons displayed, "不支持: {reason}" is shown
