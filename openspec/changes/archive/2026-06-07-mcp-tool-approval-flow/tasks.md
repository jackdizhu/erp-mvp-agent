# Tasks: MCP Tool Approval Flow

## Implementation Order

### Phase 1: Core Infrastructure

- [x] **T1.1** Create `erp_mcp_service/config.py` with APPROVAL_TTL and APPROVAL_MAX_PENDING
- [x] **T1.2** Create `erp_mcp_service/approval_manager.py` with PendingAction dataclass and ApprovalManager class
- [x] **T1.3** Create `erp_mcp_service/approval_detail.py` as thin wrapper of erp_app/approval_detail
- [x] **T1.4** Create global `approval_manager` instance in `erp_mcp_service/`

### Phase 2: Tool Schema Extension

- [x] **T2.1** Extend `erp_app/tools.py` TOOL_SCHEMAS with riskLevel, requiresApproval, irreversible, approvalSummary for:
  - [x] update_order
  - [x] cancel_order
  - [x] delete_order
  - [x] adjust_inventory

### Phase 3: MCP Service Integration

- [x] **T3.1** Modify `erp_mcp_service/tools.py` list_tools() to include metadata field
- [x] **T3.2** Add mcp_confirm_approval to TOOL_SCHEMAS
- [x] **T3.3** Modify call_tool() to check requiresApproval and intercept if needed
- [x] **T3.4** Implement _handle_confirm_approval() function
- [x] **T3.5** Add _check_requires_approval() and _get_risk_level() helper functions

### Phase 4: Cleanup & Verification

- [x] **T4.1** Add approval_manager.cleanup() call in main.py startup or periodic
- [x] **T4.2** Update imports in erp_mcp_service/__init__.py (optional - via tools.py)
- [x] **T4.3** Add unit tests for ApprovalManager
- [x] **T4.4** Add integration test for approval flow

## Task Details

### T1.1: Config Extension

**File**: `erp_mcp_service/config.py`
**Changes**: Add APPROVAL_TTL, APPROVAL_MAX_PENDING constants

### T1.2: Approval Manager

**File**: `erp_mcp_service/approval_manager.py`
**Classes**: PendingAction, ApprovalManager
**Methods**:
- `create(tool_name, arguments, risk_level, approval_detail, ttl)`
- `confirm(action_id)` → (success, error)
- `reject(action_id)` → (success, error)
- `get(action_id)` → PendingAction | None
- `cleanup()`

### T1.3: Approval Detail Wrapper

**File**: `erp_mcp_service/approval_detail.py`
**Function**: get_approval_detail(tool_name, args) → dict

### T2.1: Tool Schema Extension

**File**: `erp_app/tools.py`
**Changes**: Add to each DANGER tool schema:
```python
"riskLevel": "DANGER",
"requiresApproval": True,
"irreversible": False,  # or True for delete_order
"approvalSummary": "修改订单{order_id}的{field}为{value}",
```

### T3.1-3.5: MCP Service Tools Integration

**File**: `erp_mcp_service/tools.py`
**Changes**:
1. Import approval_manager, get_approval_detail
2. list_tools() adds metadata block to each tool
3. call_tool() checks requiresApproval, creates pending if needed
4. _handle_confirm_approval() implements confirm/reject logic
5. Add mcp_confirm_approval to returned tools list

## Verification Commands

```bash
# Start MCP service
cd erp_mvp-agent/erp_mcp_service
python main.py &

# Test tools/list includes metadata
curl -X POST http://localhost:9001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Test approval interception (should return PENDING)
curl -X POST http://localhost:9001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{
    "name":"mcp_update_order",
    "arguments":{"order_id":"ORD-001","field":"address","value":"北京"}
  }}'

# Test confirm_approval
curl -X POST http://localhost:9001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
    "name":"mcp_confirm_approval",
    "arguments":{"action_id":"act_xxx","approved":true}
  }}'
```