## ADDED Requirements

### Requirement: Frontend API port from environment variable
The frontend SHALL read the API port from `VITE_API_PORT` environment variable, with a default value of 9000. The API base URL SHALL be constructed as `http://localhost:${port}`.

#### Scenario: Environment variable is set
- **WHEN** `VITE_API_PORT` is defined in `.default.env` or `.development.env`
- **THEN** `API_BASE` SHALL use the value from `VITE_API_PORT`

#### Scenario: Environment variable is not set
- **WHEN** `VITE_API_PORT` is not defined
- **THEN** `API_BASE` SHALL default to `http://localhost:9000`
