# Proposal: Unify Approval Data Format

## Context

Currently the approval flow has two different data formats between `app/approval_core.py` and `erp_mcp_service/tools.py`. This causes the frontend `ApprovalCard` component to fail rendering because it expects `detail` but MCP returns `approval_detail`.

## What

1. **Standardize pending action format** across both implementations
2. **Add data validation** for approval response schemas
3. **Update both services** to use consistent field names and types

## Target Format

```python
{
    "status": "PENDING",                    # Required: always "PENDING"
    "action_id": "act_xxx",                 # Required: unique identifier
    "tool": "update_order",                  # Required: tool name
    "args": {"order_id": "123", ...},       # Required: tool arguments
    "risk_level": "DANGER",                 # Required: SAFE | WARNING | DANGER
    "title": "修改订单",                      # Required: human-readable title
    "summary": "修改订单123的address",         # Required: filled template
    "description": "将订单123的收货地址...",  # Required: change description
    "warning": None,                         # Required: null or warning message
    "detail": {                             # Required: structured detail
        "action_type": "update_order",
        "fields": [...],
        "changes": [...],
        "irreversible": False
    },
    "expires_at": 1717200300.0,             # Required: float timestamp
    "ttl_seconds": 300                       # Required: seconds until expiry
}
```

## Why

- Frontend `ApprovalCard` expects consistent format
- Data validation prevents runtime errors
- Easier debugging with standardized structure
- Clear contract between backend services

## Scope

### In Scope

- Update `app/approval_core.py` to new format
- Update `erp_mcp_service/tools.py` to new format
- Update `erp_app/approval_detail.py` to include new fields
- Add validation schema in `erp_app/schemas.py`
- Update `app/main.py` Pydantic models

### Out of Scope

- Frontend component changes
- MCP protocol changes
- Persistent storage format

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing approvals | High | TTL ensures old data expires quickly |
| Validation overhead | Low | Add opt-in validation flag |