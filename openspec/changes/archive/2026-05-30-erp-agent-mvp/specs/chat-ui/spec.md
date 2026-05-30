## ADDED Requirements

### Requirement: Chat page layout
The system SHALL render a single ChatPage with a collapsible session sidebar on the left and a chat area on the right, using React + Vite + native CSS.

#### Scenario: Page loads with sidebar and chat area
- **WHEN** user opens the application
- **THEN** chat page renders with sidebar showing session list and chat area showing active session messages

### Requirement: Message rendering
The system SHALL render user messages and agent replies in the chat area, with distinct visual styling for each role. Agent messages SHALL display tool_calls and pending_actions when present.

#### Scenario: User message displayed
- **WHEN** a message with role="user" exists in the session
- **THEN** it renders with user styling (right-aligned or distinct color)

#### Scenario: Agent reply with tool calls displayed
- **WHEN** an agent message contains tool_calls
- **THEN** tool call details (tool name, args, result summary) are rendered below the reply text

### Requirement: Approval card component
The system SHALL render an ApprovalCard component for each pending_action in an agent message, displaying action_type, fields, risk_level, and confirm/cancel buttons. Each card operates independently.

#### Scenario: Single approval card rendered
- **WHEN** agent message contains one pending_action
- **THEN** one approval card renders with operation details and confirm/cancel buttons

#### Scenario: Multiple approval cards rendered independently
- **WHEN** agent message contains two pending_actions
- **THEN** two separate approval cards render, each with its own confirm/cancel buttons

#### Scenario: Confirm button triggers /chat/confirm
- **WHEN** user clicks confirm on an approval card
- **THEN** POST /chat/confirm is called with the card's action_id and approved=true

#### Scenario: Cancel button triggers /chat/confirm
- **WHEN** user clicks cancel on an approval card
- **THEN** POST /chat/confirm is called with the card's action_id and approved=false

### Requirement: Approval card state transitions
The system SHALL visually update approval cards through states: PENDING (red border, buttons visible), CONFIRMED/EXECUTING (yellow, "执行中..."), SUCCESS (green, result shown), FAILED (red, error shown), REJECTED (gray, "已取消"), EXPIRED (gray, "已过期").

#### Scenario: Card transitions from pending to success
- **WHEN** user confirms a card and execution succeeds
- **THEN** card border turns green, buttons disappear, result is displayed

#### Scenario: Card transitions from pending to rejected
- **WHEN** user cancels a card
- **THEN** card border turns gray, buttons disappear, "已取消" is displayed

#### Scenario: Card shows expired state
- **WHEN** a pending card's TTL has expired
- **THEN** card border turns gray, buttons are disabled, "已过期" is displayed

### Requirement: Input area with send button
The system SHALL render an input area with a text input and send button. During pending approval state, the input area SHALL be disabled.

#### Scenario: Send message
- **WHEN** user types a message and clicks send or presses Enter
- **THEN** message is sent via POST /chat and added to the session

#### Scenario: Input disabled during approval
- **WHEN** there are pending approval cards in PENDING state
- **THEN** input area is disabled with a hint "请先处理待确认操作"

#### Scenario: Input re-enabled after all approvals resolved
- **WHEN** all pending approval cards are in a final state (SUCCESS/FAILED/REJECTED/EXPIRED)
- **THEN** input area is re-enabled

### Requirement: Session sidebar
The system SHALL render a collapsible sidebar showing session list with titles and timestamps, a "新建会话" button, and allow switching/deleting sessions.

#### Scenario: Sidebar shows sessions
- **WHEN** page loads with existing sessions
- **THEN** sidebar lists all sessions with title and creation time, active session highlighted

#### Scenario: Create new session
- **WHEN** user clicks "新建会话"
- **THEN** a new empty session is created and becomes active

#### Scenario: Delete session
- **WHEN** user clicks delete on a session
- **THEN** session is removed from list and localStorage

### Requirement: DANGER operation irreversible warning
The system SHALL display a "此操作不可撤销" warning on approval cards for irreversible operations (delete_order).

#### Scenario: Delete order shows irreversible warning
- **WHEN** approval card for delete_order is rendered
- **THEN** card displays "⚠️ 此操作不可撤销" warning text
