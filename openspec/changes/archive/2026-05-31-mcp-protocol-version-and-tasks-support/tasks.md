## 1. Protocol Version Upgrade

- [x] 1.1 Update `PROTOCOL_VERSION` in `erp_mcp_service/main.py` to `2025-11-25`
- [x] 1.2 Update `PROTOCOL_VERSION` in `app/clients/mcp_client.py` to `2025-11-25`
- [x] 1.3 Update `capabilities` in initialize response to include new protocol features
- [x] 1.4 Verify IDE connection with new protocol version

## 2. Task Manager Implementation

- [x] 2.1 Create `erp_mcp_service/task_manager.py` with `TaskState` dataclass
- [x] 2.2 Implement task storage (Dict) with TTL expiration
- [x] 2.3 Implement `create_task()` method
- [x] 2.4 Implement `get_task_status()` method
- [x] 2.5 Implement `cancel_task()` method
- [x] 2.6 Implement `list_tasks()` method
- [x] 2.7 Implement `complete_task()` method

## 3. Tasks API Endpoints

- [x] 3.1 Implement `tasks/status` endpoint in `erp_mcp_service/main.py`
- [x] 3.2 Implement `tasks/complete` endpoint
- [x] 3.3 Implement `tasks/cancel` endpoint
- [x] 3.4 Implement `tasks/list` endpoint

## 4. Tools/Call Task Integration

- [x] 4.1 Modify `tools/call` handler to detect `task` parameter
- [x] 4.2 If task present and tool supports tasks: create task, return taskId immediately
- [x] 4.3 If task present and tool forbids tasks: return error `-32601`
- [x] 4.4 If no task present: execute synchronously (current behavior)
- [x] 4.5 Run tool asynchronously and update task state on completion

## 5. Tool TaskSupport Declaration

- [x] 5.1 Update `tools/list` response to include `execution.taskSupport` for each tool
- [x] 5.2 Set `query_orders` → `taskSupport: "optional"`
- [x] 5.3 Set `query_order` → `taskSupport: "forbidden"`
- [x] 5.4 Set `create_order` → `taskSupport: "forbidden"`
- [x] 5.5 Set `update_order` → `taskSupport: "forbidden"`
- [x] 5.6 Set `query_supplier` → `taskSupport: "optional"`
- [x] 5.7 Set `cancel_order` → `taskSupport: "forbidden"`
- [x] 5.8 Set `query_inventory` → `taskSupport: "optional"`
- [x] 5.9 Set `adjust_inventory` → `taskSupport: "forbidden"`

## 6. Testing

- [x] 6.1 Test IDE connection with protocol version `2025-11-25`
- [x] 6.2 Test `query_orders` with task parameter returns taskId immediately
- [x] 6.3 Test `tasks/status` polling returns correct progress
- [x] 6.4 Test `tasks/cancel` interrupts running task
- [x] 6.5 Test `query_order` with task parameter returns error
- [x] 6.6 Test task TTL expiration cleanup