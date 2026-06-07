## Purpose

Define the approval store implementation that manages approval records with TTL, validation, and decision tracking.

## Requirements

### Requirement: Approval record creation
The system SHALL create an ApprovalRecord with action_id, tool, args, detail, created_at when a DANGER tool pending action is created, storing it in ApprovalStore.

#### Scenario: Create approval record for DANGER tool
- **WHEN** approval_store.create("act_abc123", "update_order", {"order_id": "123", "field": "address", "value": "北京"}, detail) is called
- **THEN** system creates ApprovalRecord with action_id="act_abc123", tool="update_order", supported=True, user_op_id=None, approved=None, and stores it in _records dict

### Requirement: Approval record validation
The system SHALL validate whether an approval action is supported via approval_store.validate(action_id), checking action existence, decision status, and field format.

#### Scenario: Validate existing undecided action
- **WHEN** approval_store.validate("act_abc123") is called and record exists and not decided
- **THEN** returns (True, None)

#### Scenario: Validate non-existent action
- **WHEN** approval_store.validate("act_unknown") is called
- **THEN** returns (False, "ACTION_NOT_FOUND")

#### Scenario: Validate already decided action
- **WHEN** approval_store.validate("act_abc123") is called and record has decided_at set
- **THEN** returns (False, "ALREADY_DECIDED")

### Requirement: Mark approval as unsupported
The system SHALL support marking an approval as unsupported via approval_store.mark_unsupported(action_id, reason), setting supported=False and reason.

#### Scenario: Mark unsupported with reason
- **WHEN** approval_store.mark_unsupported("act_abc123", "ORDER_NOT_FOUND") is called
- **THEN** record.supported becomes False and record.reason becomes "ORDER_NOT_FOUND"

### Requirement: User approval decision with user_op_id generation
The system SHALL generate a unique user_op_id (format: uop_{uuid4.hex[:12]}) when a user makes an approval decision via approval_store.decide(action_id, approved).

#### Scenario: Approve action generates user_op_id
- **WHEN** approval_store.decide("act_abc123", True) is called
- **THEN** returns (True, "uop_xxxxxxxxxxxx", None), record.user_op_id is set, record.approved is True, record.decided_at is set

#### Scenario: Reject action generates user_op_id
- **WHEN** approval_store.decide("act_abc123", False) is called
- **THEN** returns (True, "uop_xxxxxxxxxxxx", None), record.user_op_id is set, record.approved is False, record.decided_at is set

#### Scenario: Decide on non-existent action
- **WHEN** approval_store.decide("act_unknown", True) is called
- **THEN** returns (False, None, "ACTION_NOT_FOUND")

#### Scenario: Decide on unsupported action
- **WHEN** approval_store.decide("act_abc123", True) is called and record.supported is False
- **THEN** returns (False, None, "NOT_SUPPORTED")

#### Scenario: Decide on already decided action
- **WHEN** approval_store.decide("act_abc123", True) is called and record.user_op_id is already set
- **THEN** returns (False, None, "ALREADY_DECIDED")

### Requirement: Approval record retrieval
The system SHALL provide approval_store.get(action_id) to retrieve an ApprovalRecord by action_id.

#### Scenario: Get existing record
- **WHEN** approval_store.get("act_abc123") is called and record exists
- **THEN** returns the ApprovalRecord instance

#### Scenario: Get non-existent record
- **WHEN** approval_store.get("act_unknown") is called
- **THEN** returns None

### Requirement: Expired approval cleanup
The system SHALL clean up expired (TTL > 300 seconds) and undecided approval records on each create() call, with max_pending=10 limit.

#### Scenario: Cleanup expired records on create
- **WHEN** a new approval is created and existing records have exceeded TTL without being decided
- **THEN** expired records are removed before creating the new record

#### Scenario: Max pending limit exceeded
- **WHEN** approval_store.create() is called and _records count >= 10
- **THEN** raises ValueError("MAX_PENDING_EXCEEDED")

### Requirement: Approval record serialization
The system SHALL provide ApprovalRecord.to_dict() method that returns a dict with all record fields.

#### Scenario: Serialize record to dict
- **WHEN** record.to_dict() is called
- **THEN** returns dict with keys: action_id, tool, args, detail, supported, reason, user_op_id, approved, created_at, decided_at