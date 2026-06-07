# Tasks: Unify Approval Data Format

## Implementation Order

### Phase 1: Schema Definition

- [x] **T1.1** Create `erp_app/schemas.py` with PendingActionSchema and validate function

### Phase 2: Update erp_mcp_service

- [x] **T2.1** Update `erp_mcp_service/tools.py` call_tool() to return unified format

### Phase 3: Update app layer

- [x] **T3.1** Update `app/approval_core.py` create_pending() to return unified format
- [x] **T3.2** Update `app/main.py` PendingAction Pydantic model
- [x] **T3.3** Update `app/erp_client.py` get_approval_detail() to include new fields

### Phase 4: Update approval_detail

- [x] **T4.1** Update `erp_app/approval_detail.py` to include title, description, warning

### Phase 5: Documentation

- [x] **T5.1** Update tasks.md with completed status

## Task Details

### T1.1: Create Validation Schema

**File**: `erp_app/schemas.py`

**Functions**:
- `PendingActionSchema` - Pydantic model
- `validate_pending_action(data)` - Returns (valid, error_message)

### T2.1: Update MCP tools.py

**File**: `erp_mcp_service/tools.py`

**Changes**:
1. In call_tool() PENDING response, add:
   - `tool`: original_name
   - `args`: arguments
   - `title`: from approval_detail or _get_operation_title()
   - `summary`: from approval_detail.action_summary or summary
   - `description`: from approval_detail.description
   - `warning`: from approval_detail.warning
   - Rename `approval_detail` -> `detail`

### T3.1: Update approval_core.py

**File**: `app/approval_core.py`

**Changes**:
1. In create_pending(), update returned dict:
   - Add `status: "PENDING"`
   - Rename `id` -> `action_id`
   - Add `title`, `description`, `warning`, `ttl_seconds`
   - Keep `messages_context` (app-layer only)

### T3.2: Update Pydantic models

**File**: `app/main.py`

**Changes**:
```python
class PendingAction(BaseModel):
    status: str = "PENDING"
    action_id: str
    tool: str
    args: dict
    risk_level: str
    title: str
    summary: str
    description: str
    warning: Optional[str] = None
    detail: dict
    expires_at: float
    ttl_seconds: int
```

### T3.3: Update erp_client.py

**File**: `app/erp_client.py`

**Changes**:
- Extract title, description, warning from generate_approval_detail()
- Return structured detail object

### T4.1: Update approval_detail.py

**File**: `erp_app/approval_detail.py`

**Changes**:
- Ensure generate_approval_detail() returns detail with:
  - `action_type`, `fields`, `changes`, `irreversible`
- Title, description, warning at top level

## Verification

```bash
# Test validation
cd erp-mvp-agent
python -c "
from erp_app.schemas import validate_pending_action
action = {
    'status': 'PENDING',
    'action_id': 'act_abc12345',
    'tool': 'update_order',
    'args': {'order_id': '123'},
    'risk_level': 'DANGER',
    'title': '修改订单',
    'summary': '修改订单123的address',
    'description': '将地址从A改为B',
    'warning': None,
    'detail': {
        'action_type': 'update_order',
        'fields': [],
        'changes': [],
        'irreversible': False
    },
    'expires_at': 1717200000.0,
    'ttl_seconds': 300
}
valid, err = validate_pending_action(action)
print(f'Valid: {valid}, Error: {err}')
"
```

## Files Modified

| File | Changes |
|------|---------|
| `erp_app/schemas.py` | NEW: Validation schema |
| `erp_mcp_service/tools.py` | Update call_tool() response |
| `app/approval_core.py` | Update create_pending() response |
| `app/main.py` | Update PendingAction model |
| `app/erp_client.py` | Update get_approval_detail() return |