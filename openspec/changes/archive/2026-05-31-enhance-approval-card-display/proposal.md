# Proposal: Enhance Approval Card Display

## Context

The current approval detail structure returned from MCP service lacks front-end card display information. The `approval_detail` object only contains raw `fields` array without title, description, warning, or filled summary - making it difficult for the frontend to render an intuitive approval card.

## What

Enhance the approval detail structure with card-friendly fields:

1. **Card Title**: Human-readable operation title (e.g., "修改订单")
2. **Action Summary**: Filled template string (e.g., "修改订单 ORD-001 的 address 为 北京")
3. **Description**: Concise change description (e.g., "将地址从'旧地址'修改为'北京'")
4. **Warning Message**: Risk warning when `irreversible=true` (e.g., "⚠️ 此操作不可逆，请确认")
5. **Changes Array**: Structured field-level changes with old/new values
6. **Status Badge**: Visual risk level indicator (DANGER/WARNING/SAFE)

## Why

- Frontend needs structured data to render approval cards
- Users need clear understanding of what will change before approving
- Risk warnings help prevent accidental destructive operations
- Filled summaries enable quick scanning without parsing template placeholders

## Scope

### In Scope

- Enhance `erp_app/approval_detail.py` generate_approval_detail() to return enriched structure
- Update `erp_mcp_service/tools.py` to pass through new fields
- Add summary template filling logic
- Add changes array with old/new comparison

### Out of Scope

- Frontend card component changes
- Persistent storage of approval history
- Multi-language support

## Approach

### Data Structure Enhancement

```python
# Before
{
    "action_type": "update_order",
    "fields": [{"name": "订单编号", "value": "ORD-001"}],
    "irreversible": False
}

# After
{
    "action_type": "update_order",
    "title": "修改订单",
    "action_summary": "修改订单 ORD-001 的 address 为 北京",
    "description": "将订单 ORD-001 的地址从'旧地址'修改为'北京'",
    "warning": None,
    "fields": [...],
    "changes": [
        {"field": "address", "label": "地址", "old": "旧地址", "new": "北京"}
    ],
    "irreversible": False,
    "risk_level": "DANGER"
}
```

### Implementation

1. Extend `generate_approval_detail()` to build enriched structure
2. Fill `approvalSummary` template with actual args values
3. Generate description based on operation type
4. Add conditional warning for irreversible operations
5. Build changes array with old/new value comparison

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template placeholder mismatch | Low | Low | Fallback to generic summary |
| Missing old value (order not found) | Low | Low | Show "未知" as placeholder |

## Success Metrics

- All DANGER tool approvals return structured card data
- Frontend can render card without additional data transformation
- Irreversible operations show warning message