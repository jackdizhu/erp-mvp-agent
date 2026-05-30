## Purpose

Define session management including creation, switching, deletion, localStorage persistence, and history window truncation for the ERP agent frontend.

## Requirements

### Requirement: Session creation with auto-generated title
The system SHALL allow creating a new session with a unique ID, empty messages array, and title auto-generated from the first user message.

#### Scenario: New session created
- **WHEN** user clicks "新建会话" button
- **THEN** a new session with unique ID is created, added to sessions list, and set as active

#### Scenario: Title auto-generated from first message
- **WHEN** user sends first message "查询订单123状态" in a new session
- **THEN** session title is set to "查询订单123状态" (truncated to 20 chars if needed)

### Requirement: Session switching
The system SHALL allow switching between sessions, loading the selected session's messages into the chat view.

#### Scenario: Switch to existing session
- **WHEN** user clicks on a session in the sidebar
- **THEN** chat view loads that session's messages, and the session becomes active

### Requirement: Session deletion
The system SHALL allow deleting a session, removing it from the sessions list and localStorage.

#### Scenario: Delete a session
- **WHEN** user deletes session "sess_abc123"
- **THEN** session is removed from sessions list and localStorage, if it was active, switch to the most recent session

### Requirement: localStorage persistence
The system SHALL persist all sessions and their messages to localStorage on every state change, and restore them on page load.

#### Scenario: State persisted on message
- **WHEN** a new message is added to the active session
- **THEN** entire sessions array is serialized and saved to localStorage key "erp_agent_sessions"

#### Scenario: State restored on page load
- **WHEN** user opens the page
- **THEN** sessions are loaded from localStorage, most recent session becomes active

### Requirement: History window truncation for API calls
The system SHALL truncate the active session's messages to the most recent N=6 messages before sending as history in the /chat request.

#### Scenario: Long conversation truncated
- **WHEN** active session has 20 messages and user sends a new message
- **THEN** only the most recent 6 messages are included in the history field of the /chat request

### Requirement: Pending action state persisted in session
The system SHALL store pending_action data within the session's messages, so that approval cards survive page refresh.

#### Scenario: Pending action persisted
- **WHEN** a pending action is received from the API
- **THEN** it is stored in the current assistant message's pending_actions array and persisted to localStorage

#### Scenario: Approval card restored after refresh
- **WHEN** user refreshes the page while a pending action exists
- **THEN** the approval card is re-rendered from the persisted data
