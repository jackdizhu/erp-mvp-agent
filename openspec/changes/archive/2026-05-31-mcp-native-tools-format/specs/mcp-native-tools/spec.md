## ADDED Requirements

### Requirement: MCP Native Tools Format
All tools in the system SHALL use the MCP native format with `name`, `description`, and `inputSchema` fields.

#### Scenario: Tool Schema Structure
- **WHEN** a tool is defined
- **THEN** it SHALL have the following structure:
  ```json
  {
    "name": "tool_name",
    "description": "Tool description in Chinese",
    "inputSchema": {
      "type": "object",
      "properties": {...},
      "required": [...]
    }
  }
  ```

#### Scenario: Tool Listing
- **WHEN** `tools/list` is called on the MCP service
- **THEN** the service SHALL return an array of tools in MCP native format
- **AND** each tool SHALL have `name` (string) and `inputSchema` (object) fields

#### Scenario: Tool Execution
- **WHEN** `tools/call` is called with tool name and arguments
- **THEN** the service SHALL execute the tool and return the result
- **AND** the result SHALL follow the tool's defined return format

## MODIFIED Requirements

### Requirement: Tool Registration
- **BEFORE**: Tools were registered with OpenAI function calling format
- **AFTER**: Tools are registered with MCP native format

## REMOVED Requirements

### Requirement: OpenAI Function Calling Format
- **REMOVED**: The `TOOL_SCHEMAS` using OpenAI format `{type: "function", function: {...}}` is deprecated and replaced with MCP native format