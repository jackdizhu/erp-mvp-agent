## Purpose

Define the HTTP API endpoints for approval actions, including creation, decision, and data models.

## Requirements

### Requirement: Approval create API endpoint
The system SHALL provide POST /api/approval/create endpoint that accepts ApprovalCreateRequest (action_id, tool, args, session_id) and returns ApprovalCreateResponse (supported, action_id, reason, fields, irreversible, warning).

#### Scenario: Create approval for valid action
- **WHEN** POST /api/approval/create is called with valid action_id that exists in approval_store
- **THEN** returns ApprovalCreateResponse with supported=True, action_id, fields from record.detail, irreversible and warning from record.detail

#### Scenario: Create approval for non-existent action
- **WHEN** POST /api/approval/create is called with action_id not in approval_store
- **THEN** returns ApprovalCreateResponse with supported=False, action_id, reason="ACTION_NOT_FOUND"

#### Scenario: Create approval for already decided action
- **WHEN** POST /api/approval/create is called with action_id that has already been decided
- **THEN** returns ApprovalCreateResponse with supported=False, action_id, reason="ALREADY_DECIDED"

### Requirement: Approval decide API endpoint
The system SHALL provide POST /api/approval/decide endpoint that accepts ApprovalDecideRequest (action_id, approved, session_id) and returns ApprovalDecideResponse (user_op_id, action_id, approved, status).

#### Scenario: Approve action successfully
- **WHEN** POST /api/approval/decide is called with action_id="act_abc123" and approved=true
- **THEN** returns ApprovalDecideResponse with user_op_id="uop_xxxxxxxxxxxx", action_id="act_abc123", approved=true, status="approved"

#### Scenario: Reject action successfully
- **WHEN** POST /api/approval/decide is called with action_id="act_abc123" and approved=false
- **THEN** returns ApprovalDecideResponse with user_op_id="uop_xxxxxxxxxxxx", action_id="act_abc123", approved=false, status="rejected"

#### Scenario: Decide on invalid action
- **WHEN** POST /api/approval/decide is called with action_id not found or already decided or not supported
- **THEN** returns HTTP 400 with error detail (ACTION_NOT_FOUND / ALREADY_DECIDED / NOT_SUPPORTED)

### Requirement: Approval API data models
The system SHALL define Pydantic models in app/models.py: ApprovalCreateRequest, ApprovalCreateResponse, ApprovalDecideRequest, ApprovalDecideResponse with the specified fields.

#### Scenario: ApprovalCreateRequest validation
- **WHEN** ApprovalCreateRequest is instantiated with action_id="act_abc123", tool="update_order", args={"order_id": "123"}
- **THEN** model validates successfully with session_id=None (optional)

#### Scenario: ApprovalCreateResponse with unsupported action
- **WHEN** ApprovalCreateResponse is created with supported=False, action_id="act_abc123", reason="ORDER_NOT_FOUND"
- **THEN** fields defaults to [], irreversible defaults to False, warning defaults to None

#### Scenario: ApprovalDecideRequest validation
- **WHEN** ApprovalDecideRequest is instantiated with action_id="act_abc123", approved=true
- **THEN** model validates successfully with session_id=None (optional)