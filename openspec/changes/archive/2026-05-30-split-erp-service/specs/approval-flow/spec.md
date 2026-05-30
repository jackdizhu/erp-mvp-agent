## Purpose

Delta spec: approval flow splits into two parts - state management stays in agent (`app/approval_core.py`), detail generation moves to ERP (`erp_app/approval_detail.py`) and queries SQLite instead of directly reading memory dictionaries.

## MODIFIED Requirements

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

### Requirement: Pending action creation for DANGER tools
The system SHALL create a pending action with a unique ID, store the tool name, args, LLM messages context, and creation timestamp in `app/approval_core.py`'s pending_actions dictionary. The action summary SHALL be generated using `ACTION_SUMMARIES` templates from `erp_app/config.py`, not from `app/config.py`.

#### Scenario: DANGER tool creates pending action
- **WHEN** agent encounters a DANGER-level tool call for update_order
- **THEN** approval_core generates unique action_id, stores tool/args/messages_context/created_at, retrieves summary template from erp_app config, and returns pending_action to frontend
