## Purpose

Define the HTTP API endpoints for chat communication, including message handling, tool call transparency, and pending action confirmation.

## Requirements

### Requirement: Chat endpoint accepts message with history
The system SHALL provide a POST /chat endpoint that accepts a JSON body containing `message` (string) and `history` (array of {role, content} objects), and returns a JSON response containing `reply` (string).

#### Scenario: Simple query without history
- **WHEN** client sends POST /chat with message="查询订单123状态" and empty history
- **THEN** system returns JSON with reply field containing the agent's response

#### Scenario: Query with conversation history
- **WHEN** client sends POST /chat with message="帮我改一下收货地址" and history containing previous messages about order 123
- **THEN** system uses history context to understand "一下" refers to order 123

### Requirement: Chat response includes tool calls transparency
The system SHALL include a `tool_calls` array in the chat response, listing each tool call made during the request with its tool name, arguments, and result.

#### Scenario: Tool call returned in response
- **WHEN** agent executes query_order("123") to answer a user question
- **THEN** response includes tool_calls: [{tool: "query_order", args: {order_id: "123"}, result: {...}}]

### Requirement: Chat response includes pending action for DANGER tools
The system SHALL include a `pending_action` object in the chat response when a DANGER-level tool is invoked, containing id, tool, args, risk_level, summary, and detail fields.

#### Scenario: DANGER tool returns pending action
- **WHEN** agent determine update_order is needed
- **THEN** response includes pending_action with id, tool="update_order", risk_level="DANGER", and a human-readable summary

### Requirement: Approval create endpoint
The system SHALL provide POST /api/approval/create endpoint that validates an approval action and returns whether it is supported, along with display metadata for the approval card.

#### Scenario: Create approval for valid action
- **WHEN** client sends POST /api/approval/create with action_id="act_abc123", tool="update_order", args={...}
- **THEN** system validates via approval_store, returns {supported: true, action_id: "act_abc123", fields: [...], irreversible: false, warning: null}

#### Scenario: Create approval for invalid action
- **WHEN** client sends POST /api/approval/create with action_id="act_unknown"
- **THEN** system returns {supported: false, action_id: "act_unknown", reason: "ACTION_NOT_FOUND"}

### Requirement: Approval decide endpoint
The system SHALL provide POST /api/approval/decide endpoint that records the user's approval decision and generates a user_op_id.

#### Scenario: User approves action
- **WHEN** client sends POST /api/approval/decide with action_id="act_abc123", approved=true
- **THEN** system generates user_op_id, returns {user_op_id: "uop_xxxxxxxxxxxx", action_id: "act_abc123", approved: true, status: "approved"}

#### Scenario: User rejects action
- **WHEN** client sends POST /api/approval/decide with action_id="act_abc123", approved=false
- **THEN** system generates user_op_id, returns {user_op_id: "uop_xxxxxxxxxxxx", action_id: "act_abc123", approved: false, status: "rejected"}

#### Scenario: Decide on invalid action returns 400
- **WHEN** client sends POST /api/approval/decide with action_id not found or already decided
- **THEN** system returns HTTP 400 with error detail

### Requirement: Confirm endpoint executes or rejects pending actions
The system SHALL provide a POST /chat/confirm endpoint that accepts `action_id` (string), `approved` (boolean), `history` (array), and optional `user_op_id` (string), and returns the execution result or cancellation message. When `user_op_id` is provided, the system SHALL pass it to `confirm_action` for preapproved execution.

#### Scenario: Approved action executes successfully with user_op_id
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123", approved=true, user_op_id="uop_xxxxxxxxxxxx"
- **THEN** system executes the pending tool call with preapproved flag and returns the result

#### Scenario: Approved action executes successfully without user_op_id
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123", approved=true (no user_op_id)
- **THEN** system executes the pending tool call normally (backward compatible)

#### Scenario: Rejected action returns cancellation message
- **WHEN** client sends POST /chat/confirm with action_id="act_abc123" and approved=false
- **THEN** system returns reply="操作已取消" and clears the pending action

#### Scenario: Expired action returns error
- **WHEN** client sends POST /chat/confirm with an expired action_id
- **THEN** system returns error with code TOOL_EXPIRED and message="操作已过期，请重新发起"

### Requirement: History window truncation
The system SHALL truncate the history array to the most recent N=6 messages before sending to LLM, where N is configurable via config.py.

#### Scenario: History exceeds window size
- **WHEN** client sends 10 messages in history
- **THEN** system only sends the most recent 6 messages to the LLM

### Requirement: Skill available endpoint
The system SHALL provide `GET /api/skills/available` that returns an array of all registered skills (preset + custom) with fields: name, description, category, tools, has_workflow, has_handler.

#### Scenario: Returns all skills
- **WHEN** registry has 2 preset + 1 custom skill loaded
- **THEN** endpoint returns JSON array of 3 objects with all required fields

#### Scenario: Empty registry
- **WHEN** no skills are registered (registry is None or empty)
- **THEN** endpoint returns empty array (HTTP 200)

### Requirement: Skill loaded endpoint
The system SHALL provide `GET /api/skills/loaded` that returns currently active skills for the session with name, description, category.

#### Scenario: Returns loaded skills
- **WHEN** session has loaded skills
- **THEN** endpoint returns their metadata as JSON array

### Requirement: Skill load endpoint
The system SHALL provide `POST /api/skills/load` with request body `{"skill_name": "..."}` (Pydantic model `SkillLoadRequest`) that validates the skill exists in the registry and returns its metadata.

#### Scenario: Skill exists returns metadata
- **WHEN** POST with skill_name="batch-query-order" present in registry
- **THEN** returns HTTP 200 with `{success: True, name: "batch-query-order", tools: [...], has_workflow: True, has_handler: False}`

#### Scenario: Skill not found returns 404
- **WHEN** skill_name is not in registry
- **THEN** returns HTTP 404 with `{"detail": "Skill 'xxx' not found"}`

#### Scenario: Registry not initialized returns 500
- **WHEN** get_skill_registry() returns None
- **THEN** returns HTTP 500 with `{"detail": "Skill registry not initialized"}`

### Requirement: Skill validate endpoint
The system SHALL provide `POST /api/skills/validate` with request body `{"skill_name": "...", "skill_data": {...}}` (Pydantic model `SkillValidateRequest`) that runs `SkillValidator.validate_config` against the config and returns `{valid: bool, errors: []}`.

#### Scenario: Valid custom skill config
- **WHEN** skill_data has valid name, description, intent_patterns, tools, workflow.steps and all tools are in available_tools
- **THEN** returns HTTP 200 with `{valid: True, errors: []}`

#### Scenario: Invalid config returns errors
- **WHEN** skill_data is missing description OR has unknown tool OR contains security blacklist keyword
- **THEN** returns HTTP 200 with `{valid: False, errors: [...detailed error messages...]}`

### Requirement: Skill create endpoint
The system SHALL provide `POST /api/skills/create` with request body `{name, description, intent_patterns, prompt_fragment?, tools, workflow?}` (Pydantic model `SkillCreateRequest`) that writes a new custom skill to disk and hot-loads it into the registry.

#### Scenario: Successful creation
- **WHEN** POST with name="my-skill" matching `^[a-zA-Z0-9_-]+$`, valid description, valid intent_patterns, valid tools, valid workflow
- **THEN** writes `skills_custom/my-skill/skill.yaml`
- **AND** calls `registry.add_skill(config)` to hot-reload
- **AND** returns HTTP 200 with `{success: True, name: "my-skill"}`

#### Scenario: Invalid name format returns 400
- **WHEN** name contains spaces, slashes, or non-`[a-zA-Z0-9_-]` chars
- **THEN** returns HTTP 400 with `{"detail": "Skill 名称只允许字母、数字、下划线和连字符"}`

#### Scenario: Name collision returns 400
- **WHEN** name already exists in registry
- **THEN** returns HTTP 400 with `{"detail": "Skill 'xxx' 已存在"}`

#### Scenario: Validation failure returns 400
- **WHEN** skill_data fails SkillValidator (missing field, unknown tool, security violation)
- **THEN** returns HTTP 400 with `{"detail": "<joined error messages>"}`

#### Scenario: Directory auto-created
- **WHEN** skills_custom/{name}/ does not exist
- **THEN** system creates it with `mkdir(parents=True, exist_ok=True)` before writing skill.yaml

### Requirement: Skill API request models
The system SHALL define Pydantic BaseModel classes for the three POST endpoints: `SkillLoadRequest(skill_name: str)`, `SkillValidateRequest(skill_name: str, skill_data: dict)`, `SkillCreateRequest(name, description, intent_patterns, prompt_fragment="", tools=[], workflow=None)`.

#### Scenario: SkillCreateRequest workflow as nested dict
- **WHEN** request body has `workflow: {steps: [{id: "x", type: "tool_call", ...}]}`
- **THEN** SkillCreateRequest parses workflow.steps as List[Dict] (workflow itself stays as nested dict for validator)

#### Scenario: Missing required field rejected
- **WHEN** SkillCreateRequest request body lacks `name`
- **THEN** FastAPI returns HTTP 422 with field validation error
