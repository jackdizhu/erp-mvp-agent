## Purpose

Define the pending action lifecycle including creation, TTL expiration, confirmation, and cleanup for DANGER-level tool operations.

## Requirements

### Requirement: Pending action creation for DANGER tools
The system SHALL create a pending action with a unique ID, store the tool name, args, LLM messages context, and creation timestamp in memory when a DANGER-level tool is invoked.

#### Scenario: DANGER tool creates pending action
- **WHEN** agent encounters a DANGER-level tool call for update_order
- **THEN** approval_core generates unique action_id, stores tool/args/messages_context/created_at, retrieves summary template from erp_app config, and returns pending_action to frontend

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

### Requirement: Action summary generation source
The system SHALL generate a human-readable summary for each pending action using `ACTION_SUMMARIES` templates from `erp_app/config.py`, not from `app/config.py`.

### Requirement: Action detail for approval card
The system SHALL generate a detail object for each pending action by calling `erp_app/approval_detail.py`, which queries SQLite to get the original data (e.g., order's current status) and compares old vs new values. The detail SHALL contain action_type, fields array (name-value pairs), and irreversible flag. Direct dictionary access to `mock_erp.orders`/`inventory` SHALL NOT be used.

#### Scenario: Delete order detail
- **WHEN** pending action for delete_order(order_id="125") is created
- **THEN** erp_app queries SQLite for order 125, returns detail with action_type="delete_order", fields=[{name:"订单编号",value:"125"},{name:"当前状态",value:"cancelled"}], irreversible=true

#### Scenario: Update order detail shows old vs new
- **WHEN** pending action for update_order(order_id="123", field="address", value="北京") is created
- **THEN** erp_app queries SQLite for order 123's current address, returns fields containing both original and new address values

#### Scenario: Adjust inventory detail shows before/after
- **WHEN** pending action for adjust_inventory(sku="iPhone-15", delta=-20) is created
- **THEN** erp_app queries SQLite for current qty, returns fields with current_qty, delta, and new_qty

### Requirement: Enhanced approval detail structure
The system SHALL return approval_detail with additional fields for front-end card rendering: title, action_summary, description, warning, changes array, and risk_level.

#### Scenario: Update order enhanced detail
- **WHEN** update_order(order_id="ORD-001", field="address", value="北京") is called
- **THEN** approval_detail contains:
  - action_type: "update_order"
  - risk_level: "DANGER"
  - title: "修改订单"
  - action_summary: "修改订单 ORD-001 的 address 为 北京"
  - description: "将订单 ORD-001 的地址从'旧地址'修改为'北京'"
  - warning: null
  - changes: [{field: "address", label: "地址", old: "旧地址", new: "北京"}]
  - irreversible: false

#### Scenario: Delete order with warning
- **WHEN** delete_order(order_id="ORD-002") is called
- **THEN** approval_detail contains:
  - warning: "⚠️ 此操作不可逆，删除后将无法恢复"
  - irreversible: true

### Requirement: Template-based summary generation
The system SHALL fill `approvalSummary` template placeholders with actual argument values when generating action_summary.

#### Scenario: Template with placeholders
- **WHEN** template is "修改订单{order_id}的{field}"
- **AND** args are {"order_id": "ORD-001", "field": "address"}
- **THEN** action_summary is "修改订单 ORD-001 的 address"

#### Scenario: Missing template fallback
- **WHEN** approvalSummary is empty
- **AND** tool_name is "delete_order"
- **AND** order_id is "ORD-003"
- **THEN** action_summary is "删除订单 ORD-003"

### Requirement: Unified pending action response format
The system SHALL return pending action with standardized field names and types for all approval flows.

#### Scenario: Valid pending action format
- **WHEN** pending action is created
- **THEN** response contains:
  | Field | Type | Required | Description |
  |-------|------|----------|-------------|
  | status | string | Yes | Always "PENDING" |
  | action_id | string | Yes | Format: act_[8 hex] |
  | tool | string | Yes | Tool name |
  | args | object | Yes | Tool arguments |
  | risk_level | string | Yes | SAFE/WARNING/DANGER |
  | title | string | Yes | Operation title |
  | summary | string | Yes | Filled template |
  | description | string | Yes | Change description |
  | warning | string\|null | Yes | Warning message |
  | detail | object | Yes | ApprovalDetail |
  | expires_at | number | Yes | Unix timestamp (float) |
  | ttl_seconds | number | Yes | Seconds until expiry |

### Requirement: Approval detail changes array
The system SHALL generate a changes array showing field-level modifications with label, old, and new values.

#### Scenario: Inventory adjustment changes
- **WHEN** adjust_inventory(sku="SKU-001", delta=-20) is called
- **AND** current quantity is 100
- **THEN** changes contains:
  - {field: "qty", label: "当前库存", old: "100", new: "-"}
  - {field: "delta", label: "调整数量", old: "-", new: "-20"}
  - {field: "qty", label: "调整后库存", old: "-", new: "80"}

### Requirement: Pending action validation
The system SHALL provide validate_pending_action() function that returns (valid, error_message) tuple.

#### Scenario: Valid action validation
- **WHEN** validate_pending_action(action) is called
- **AND** action has all required fields
- **AND** all values are correct type
- **THEN** returns (true, null)

#### Scenario: Invalid action validation
- **WHEN** validate_pending_action(action) is called
- **AND** action is missing "title" field
- **THEN** returns (false, "Missing required field: title")

### Requirement: Expired actions cleanup
The system SHALL clean up expired pending actions on each new request to prevent memory leaks, with max_pending=10 limit.

#### Scenario: Cleanup on new request
- **WHEN** a new chat request arrives and pending actions contain expired entries
- **THEN** system removes all expired entries before processing
