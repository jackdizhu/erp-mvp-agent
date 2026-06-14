## ADDED Requirements

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
