# Proposal: MCP Tool Approval Flow

## Context

The erp_mcp_service provides MCP (Model Context Protocol) access to ERP tools, but lacks the approval mechanism that exists in the original erp_app local service. High-risk operations like update_order, cancel_order, delete_order, and adjust_inventory require approval before execution, but currently execute directly without any human-in-the-loop checkpoint.

## What

Implement approval flow in erp_mcp_service using Tool Metadata extension:

1. **Tool Metadata**: Extend TOOL_SCHEMAS with `riskLevel`, `requiresApproval`, `irreversible` fields
2. **Metadata Propagation**: `list_tools()` exposes metadata in MCP protocol response
3. **Approval Interception**: `tools/call` checks metadata, intercepts high-risk tools
4. **Pending Action Management**: Store pending actions with TTL, provide confirm/reject via `mcp_confirm_approval` tool
5. **Approval Detail**: Thin wrapper around erp_app/approval_detail.py for generating comparison data

## Why

- Prevent accidental execution of destructive operations
- Maintain audit trail for high-risk business operations
- Align MCP service behavior with original erp_app design
- Provide LLM with metadata to understand risk levels

## Scope

### In Scope

- Tool metadata extension in erp_app/tools.py
- Metadata aggregation in erp_mcp_service/tools.py
- Pending action storage and TTL management
- Approval interception in tools/call
- mcp_confirm_approval tool registration
- approval_detail thin wrapper

### Out of Scope

- Frontend approval UI changes (handled by agent layer)
- Persistent storage of approval history (in-memory only for MVP)
- Approval delegation or escalation workflows

## Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Service Layers                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Tool Definition (erp_app/tools.py)                     │
│  └── TOOL_SCHEMAS extended with riskLevel, requiresApproval     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Metadata Aggregation (erp_mcp_service/tools.py)        │
│  └── list_tools() injects metadata into protocol response        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Approval Interception (erp_mcp_service/main.py)        │
│  └── tools/call checks metadata, intercepts high-risk tools      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Approval Management (erp_mcp_service/approval_*.py)    │
│  └── Pending action storage, TTL, confirm/reject logic           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger Point | tools/call interception | Single point of control, consistent with MCP protocol |
| Approval API | mcp_confirm_approval tool | Reuses existing tools/call mechanism |
| Detail Generation | Thin wrapper | Avoids duplication, maintains single source |
| TTL Management | In-memory with cleanup | MVP scope, can extend to persistent later |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM doesn't read metadata | Low | Medium | Tools/call always checks, metadata is redundant safety |
| Action expires during user review | Medium | Low | Configurable TTL, clear error message |
| Race condition on concurrent approvals | Low | High | Action status check before execution |

## Success Metrics

- All DANGER-level tools (update_order, cancel_order, delete_order, adjust_inventory) require approval
- Approval interception returns valid pending_action with approval_detail
- mcp_confirm_approval successfully executes or rejects pending actions
- Expired actions return APPROVAL_EXPIRED error