## Purpose

Define tool-level task support declarations for the ERP MCP Service, specifying which tools support asynchronous task execution.

## Requirements

### Requirement: Tool taskSupport declaration
The server SHALL include `execution.taskSupport` field in each tool's metadata from `tools/list`.

#### Scenario: List tools with taskSupport
- **WHEN** client sends `tools/list` request
- **THEN** each tool includes `execution.taskSupport` field with value:
  - `optional`: Tool supports but does not require task-augmented calls
  - `required`: Tool requires task-augmented calls
  - `forbidden`: Tool does not support task-augmented calls

### Requirement: query_orders taskSupport
The `query_orders` tool SHALL declare `taskSupport: "optional"` to indicate batch queries can be executed as tasks.

#### Scenario: Batch query supports tasks
- **WHEN** client calls `query_orders` with `task` parameter
- **THEN** server creates a task and returns taskId immediately

### Requirement: Single-item operations forbid tasks
Single-item operation tools SHALL declare `taskSupport: "forbidden"`.

#### Scenario: Single order query rejects task
- **WHEN** client calls `query_order` with `task` parameter
- **THEN** server returns error `-32601` (Method not found)

### Requirement: Supplier operations taskSupport
The `list_suppliers` and `search_suppliers` tools SHALL declare `taskSupport: "optional"`.

#### Scenario: Large supplier list supports tasks
- **WHEN** client calls `list_suppliers` with `task` parameter
- **THEN** server creates a task and returns taskId immediately