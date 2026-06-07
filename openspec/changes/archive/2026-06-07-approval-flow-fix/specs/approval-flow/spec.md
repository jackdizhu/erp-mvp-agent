## MODIFIED Requirements

### Requirement: Pending action confirmation
The system SHALL execute the stored tool call when confirm(action_id, approved=True, user_op_id=None) is called, recording the user_op_id in the action result, and clear the stored data when approved=False.

#### Scenario: Confirm executes tool with user_op_id
- **WHEN** confirm("act_abc123", approved=True, user_op_id="uop_xxxxxxxxxxxx") is called
- **THEN** system retrieves stored tool call, sets result["user_op_id"]="uop_xxxxxxxxxxxx", executes it, sends result to LLM, and returns final reply

#### Scenario: Confirm executes tool without user_op_id (backward compatible)
- **WHEN** confirm("act_abc123", approved=True) is called without user_op_id
- **THEN** system retrieves stored tool call, executes it normally, result["user_op_id"] is None

#### Scenario: Reject clears action with user_op_id
- **WHEN** confirm("act_abc123", approved=False, user_op_id="uop_xxxxxxxxxxxx") is called
- **THEN** system clears the pending action, result["user_op_id"]="uop_xxxxxxxxxxxx", and returns "操作已取消"

## ADDED Requirements

### Requirement: Approval status check
The system SHALL provide check_approval_status(action_id) function that returns user_op_id and approved status if the action has been decided, or None if not yet decided or not found.

#### Scenario: Check decided approval
- **WHEN** check_approval_status("act_abc123") is called and record has user_op_id set
- **THEN** returns {"user_op_id": "uop_xxxxxxxxxxxx", "approved": True, "action_id": "act_abc123"}

#### Scenario: Check undecided approval
- **WHEN** check_approval_status("act_abc123") is called and record has no user_op_id
- **THEN** returns None

#### Scenario: Check non-existent approval
- **WHEN** check_approval_status("act_unknown") is called
- **THEN** returns None
