# Tasks: Approval Card Display Enhancement

## Implementation Order

### Phase 1: Core Logic

- [x] **T1.1** Update `erp_app/approval_detail.py` with helper functions
- [x] **T1.2** Implement `_fill_summary_template()` function
- [x] **T1.3** Implement `_generate_description()` function
- [x] **T1.4** Implement `_build_changes()` function
- [x] **T1.5** Implement `_generate_warning()` function
- [x] **T1.6** Update `generate_approval_detail()` to return enhanced structure

### Phase 2: MCP Integration

- [x] **T2.1** Update `erp_mcp_service/tools.py` to pass risk_level

### Phase 3: Documentation

- [x] **T3.1** Update tasks.md with completed status

## Task Details

### T1.1-T1.6: approval_detail.py Enhancement

**File**: `erp_app/approval_detail.py`

**Changes**:
1. Add FIELD_LABELS mapping dict
2. Add helper functions:
   - `_fill_summary_template(template, tool_name, args)`
   - `_generate_description(tool_name, args, old_values)`
   - `_build_changes(tool_name, args, old_values)`
   - `_generate_warning(irreversible, tool_name)`
   - `_get_field_label(field)`
   - `_get_operation_title(tool_name)`
3. Update `generate_approval_detail()` to build enhanced structure

### T2.1: MCP Tools Update

**File**: `erp_mcp_service/tools.py`

**Changes**: 
- Add OPERATION_TITLES and `_get_operation_title()` helper
- Update error fallback to include all new fields

## Verification

```bash
# Test approval_detail output
cd erp-mvp-agent
python -c "
from erp_app.approval_detail import generate_approval_detail
detail = generate_approval_detail('update_order', {'order_id': 'ORD-001', 'field': 'address', 'value': '北京'})
import json
print(json.dumps(detail, ensure_ascii=False, indent=2))
"
```