## ADDED Requirements

### Requirement: Stream error diagnostics
The system SHALL provide detailed error information when a streaming connection fails, including HTTP status code, status text, and error message, to assist in problem analysis.

#### Scenario: HTTP error response received
- **WHEN** the streaming endpoint returns a non-2xx HTTP status code
- **THEN** the system SHALL capture the status code, status text, and response body
- **AND** pass them to the onError callback as an error object with `status`, `statusText`, and `message` fields

#### Scenario: Network connection failure
- **WHEN** the streaming request fails due to network issues (e.g., server not reachable)
- **THEN** the error object SHALL have `status` set to 0 and `message` describing the network error

#### Scenario: Frontend displays error details
- **WHEN** the onError callback receives an error object
- **THEN** the UI SHALL display a message in the format `[status] message` (e.g., `[500] Internal Server Error`)
- **AND** if status is 0, display `[Network] Connection failed`

#### Scenario: Backend logs stream errors
- **WHEN** an exception occurs in the stream endpoint
- **THEN** the backend SHALL log the error at ERROR level with session_id and full exception traceback

#### Scenario: MCP client logs HTTP failures
- **WHEN** an MCP HTTP request fails with a non-2xx status code
- **THEN** the client SHALL log the URL, status code, response body, and duration at ERROR level
