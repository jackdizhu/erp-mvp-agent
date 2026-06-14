## Purpose

Define the REST API endpoints for Skill management: listing available/loaded skills, loading a skill on demand, validating a custom skill configuration before creation, and creating a new custom skill (writes skill.yaml to disk and hot-reloads into the registry).

## ADDED Requirements

### Requirement: List available skills
The system SHALL provide `GET /api/skills/available` that returns an array of all registered skills with fields: name, description, category, tools, has_workflow, has_handler.

#### Scenario: Returns all skills
- **WHEN** registry has 2 preset + 1 custom skill loaded
- **THEN** endpoint returns array of 3 objects with all required fields

#### Scenario: Empty registry
- **WHEN** no skills registered
- **THEN** endpoint returns empty array

### Requirement: List loaded skills
The system SHALL provide `GET /api/skills/loaded` that returns currently active (loaded) skills for the session, with name, description, category.

#### Scenario: Returns loaded skills
- **WHEN** session has loaded skills [order, inventory]
- **THEN** endpoint returns those two skills' metadata

### Requirement: Load skill on demand
The system SHALL provide `POST /api/skills/load` with body `{"skill_name": "..."}` that validates the skill exists and returns its metadata (name, tools, has_workflow, has_handler).

#### Scenario: Skill exists
- **WHEN** POST /api/skills/load with skill_name="batch-query-order"
- **THEN** returns {success: True, name: "batch-query-order", tools: [...], has_workflow: True, has_handler: False}

#### Scenario: Skill not found
- **WHEN** skill_name not in registry
- **THEN** returns HTTP 404 with detail="Skill 'xxx' not found"

#### Scenario: Registry not initialized
- **WHEN** get_skill_registry() returns None
- **THEN** returns HTTP 500 with detail="Skill registry not initialized"

### Requirement: Validate custom skill
The system SHALL provide `POST /api/skills/validate` with body `{"skill_name": "...", "skill_data": {...}}` that runs `SkillValidator.validate_config` against the provided config_data and returns `{valid: bool, errors: []}`.

#### Scenario: Valid custom skill
- **WHEN** skill_data has valid name, description, intent_patterns, tools (all in available_tools), workflow.steps
- **THEN** returns {valid: True, errors: []}

#### Scenario: Invalid tool reference
- **WHEN** skill_data tools: ["nonexistent_tool"]
- **THEN** returns {valid: False, errors: ["工具 'nonexistent_tool' 未在当前 MCP 注册表中..."]}

#### Scenario: Security violation
- **WHEN** skill_data prompt_fragment contains "调用 http 接口"
- **THEN** returns {valid: False, errors: ["安全校验失败：包含禁止的操作 'http'..."]}

### Requirement: Create custom skill
The system SHALL provide `POST /api/skills/create` with body `{name, description, intent_patterns, prompt_fragment?, tools, workflow?}` that: (1) validates name matches `^[a-zA-Z0-9_-]+$`, (2) checks no name collision, (3) runs validator, (4) writes `skills_custom/{name}/skill.yaml`, (5) hot-loads into registry.

#### Scenario: Successful creation
- **WHEN** POST with valid name="my-skill" and all required fields
- **THEN** writes skill.yaml to skills_custom/my-skill/, calls registry.add_skill(), returns {success: True, name: "my-skill"}

#### Scenario: Invalid name format
- **WHEN** name contains spaces or special chars
- **THEN** returns HTTP 400 with detail="Skill 名称只允许字母、数字、下划线和连字符"

#### Scenario: Name collision
- **WHEN** name="existing-skill" already in registry
- **THEN** returns HTTP 400 with detail="Skill 'existing-skill' 已存在"

#### Scenario: Validation failure
- **WHEN** skill_data fails validator (missing description, invalid tool, security violation)
- **THEN** returns HTTP 400 with detail="; ".join(errors)

#### Scenario: Directory creation
- **WHEN** skills_custom/my-skill/ does not exist
- **THEN** mkdir(parents=True, exist_ok=True) creates it before writing skill.yaml

### Requirement: Pydantic request models
The system SHALL define Pydantic BaseModel classes in `app/main.py` (or `app/models.py`) for the three POST endpoints: `SkillLoadRequest`, `SkillValidateRequest`, `SkillCreateRequest`.

#### Scenario: SkillLoadRequest schema
- **WHEN** request body is `{"skill_name": "x"}`
- **THEN** SkillLoadRequest(skill_name="x") validates successfully

#### Scenario: SkillCreateRequest schema
- **WHEN** request body includes all fields with workflow as nested dict
- **THEN** SkillCreateRequest parses workflow.steps as List[Dict]

#### Scenario: Missing required field rejected
- **WHEN** SkillCreateRequest missing name
- **THEN** FastAPI returns 422 Unprocessable Entity
