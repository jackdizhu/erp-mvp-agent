## Purpose

Define the MCP Tasks protocol support for the ERP MCP Service, enabling asynchronous task execution, polling, cancellation, and result retrieval.

## Requirements

### Requirement: Server declares Tasks capability
The MCP server SHALL declare `tasks` capability during initialization with support for `list`, `cancel`, and `requests.tools.call`.

#### Scenario: Initialize with Tasks capability
- **WHEN** client sends `initialize` request
- **THEN** server returns capabilities including:
  ```json
  {
    "tasks": {
      "list": {},
      "cancel": {},
      "requests": {
        "tools": { "call": {} }
      }
    }
  }
  ```

### Requirement: Task creation via tools/call
The server SHALL support task-augmented `tools/call` requests when client includes `task` parameter.

#### Scenario: Create task for long-running tool
- **WHEN** client sends `tools/call` with `task: { ttl: 60000 }`
- **AND** the tool has `taskSupport` of `optional` or `required`
- **THEN** server returns immediately with:
  ```json
  {
    "task": {
      "taskId": "<uuid>",
      "status": "working"
    }
  }
  ```
- **AND** executes the tool asynchronously

#### Scenario: Reject task for forbidden tool
- **WHEN** client sends `tools/call` with `task` parameter
- **AND** the tool has `taskSupport` of `forbidden`
- **THEN** server returns error `-32601` (Method not found)

### Requirement: Task status polling
The server SHALL support `tasks/status` method for polling task progress.

#### Scenario: Poll working task
- **WHEN** client sends `tasks/status` with `taskId`
- **AND** task status is `working`
- **THEN** server returns:
  ```json
  {
    "task": {
      "taskId": "<uuid>",
      "status": "working",
      "progress": { "processed": 350, "total": 1000 }
    }
  }
  ```

#### Scenario: Poll completed task
- **WHEN** client sends `tasks/status` with `taskId`
- **AND** task status is `completed`
- **THEN** server returns:
  ```json
  {
    "task": {
      "taskId": "<uuid>",
      "status": "completed"
    }
  }
  ```

### Requirement: Task completion retrieval
The server SHALL support `tasks/complete` method for retrieving task results.

#### Scenario: Get completed task result
- **WHEN** client sends `tasks/complete` with `taskId`
- **AND** task status is `completed`
- **THEN** server returns the task result

#### Scenario: Get failed task error
- **WHEN** client sends `tasks/complete` with `taskId`
- **AND** task status is `failed`
- **THEN** server returns error with task error message

### Requirement: Task cancellation
The server SHALL support `tasks/cancel` method for canceling running tasks.

#### Scenario: Cancel working task
- **WHEN** client sends `tasks/cancel` with `taskId`
- **AND** task status is `working`
- **THEN** server sets task status to `canceled`
- **AND** interrupts the tool execution

### Requirement: Task list retrieval
The server SHALL support `tasks/list` method for listing all tasks.

#### Scenario: List all tasks
- **WHEN** client sends `tasks/list` request
- **THEN** server returns list of all tasks with their status

### Requirement: Task TTL expiration
The server SHALL automatically expire tasks after their TTL expires.

#### Scenario: Task TTL expired
- **WHEN** task TTL (time-to-live) expires
- **THEN** server removes task from storage
- **AND** returns error for subsequent status requests