## Purpose

Define the Skill framework core runtime: data structures, configuration loading, registry-based intent matching, and global lifecycle management for preset and custom skills.

## ADDED Requirements

### Requirement: Workflow data structures
The system SHALL define `WorkflowStep` (id, tool, status, args, result, error) and `WorkflowResult` (success, error, need_more_info, need_approval, intermediate_data, steps) dataclasses for skill workflow execution.

#### Scenario: WorkflowStep created
- **WHEN** a workflow step begins execution
- **THEN** a WorkflowStep with id, tool, status="pending" is created

#### Scenario: WorkflowResult success
- **WHEN** a workflow completes successfully
- **THEN** WorkflowResult has success=True, steps list populated, intermediate_data dict

#### Scenario: WorkflowResult need_approval
- **WHEN** handler returns WorkflowResult(need_approval=True)
- **THEN** intermediate_data contains tool, tool_args, approval_summary keys

### Requirement: SkillHandler base class
The system SHALL define `SkillHandler` base class with `skill_name` class attribute, `execute(message, context) -> WorkflowResult` abstract method, and optional `verify(result) -> bool` method.

#### Scenario: Handler execute
- **WHEN** subclass implements execute()
- **THEN** system calls execute(message, context) and returns WorkflowResult

#### Scenario: Handler verify default
- **WHEN** subclass does not implement verify()
- **THEN** default verify returns result.success

### Requirement: Skill config loading from skill.yaml
The system SHALL load Skill configuration from `<skill_dir>/skill.yaml` using yaml.safe_load, parsing fields: name, version, description, category, intent_patterns, tools, prompt_fragment, workflow.

#### Scenario: Valid skill.yaml loaded
- **WHEN** skill.yaml exists and is valid YAML
- **THEN** SkillConfig populates all fields from parsed dict

#### Scenario: Missing skill.yaml
- **WHEN** skill_dir contains no skill.yaml
- **THEN** loader returns False and logs warning

#### Scenario: Invalid YAML
- **WHEN** skill.yaml has invalid YAML syntax
- **THEN** loader catches exception, returns False, logs error

### Requirement: Python handler dynamic loading
The system SHALL dynamically load Python handler classes via `importlib.import_module()` when `workflow.handler` is specified in skill.yaml, with module name matching the skill's directory and class name from the dotted path.

#### Scenario: Handler loaded successfully
- **WHEN** workflow.handler = "query_order_edit_address.OrderEditAddressHandler" and handler.py exists in skill_dir
- **THEN** loader imports module and instantiates class

#### Scenario: Handler not found
- **WHEN** handler.py missing or class not in module
- **THEN** loader logs error, self.handler remains None, skill still loads

#### Scenario: Handler disabled for custom skills
- **WHEN** category="custom" and workflow.handler is specified
- **THEN** validator rejects with "Custom skill does not allow Python handler" error

### Requirement: Skill directory scanning
The system SHALL scan two root directories on startup: `skills/` for preset skills and `skills_custom/` for custom skills, both as flat lists of subdirectories each containing a skill.yaml.

#### Scenario: Preset skills scanned
- **WHEN** `skills/` contains subdirectories query-order-search/ and query-order-edit-address/
- **THEN** loader registers both skills

#### Scenario: Custom skills scanned
- **WHEN** `skills_custom/` contains subdirectory batch-query-order/
- **THEN** loader registers the custom skill

#### Scenario: Missing directories handled
- **WHEN** `skills_custom/` does not exist
- **THEN** loader logs warning, returns empty dict for custom, continues with preset

### Requirement: Intent pattern matching
The system SHALL compile and match user messages against `intent_patterns.zh` and `intent_patterns.en` regular expressions for each registered skill, returning the first matching SkillConfig.

#### Scenario: Match Chinese pattern
- **WHEN** user sends "查一下订单 ORD-001 状态"
- **THEN** registry returns query-order-search SkillConfig

#### Scenario: Match English pattern
- **WHEN** user sends "check my order status"
- **THEN** registry returns query-order-search SkillConfig (case-insensitive)

#### Scenario: No match
- **WHEN** user sends "今天天气怎么样"
- **THEN** registry returns None

#### Scenario: Invalid regex skipped
- **WHEN** a skill has an invalid regex pattern
- **THEN** loader logs warning and skips that pattern, other patterns still work

### Requirement: Global registry singleton
The system SHALL maintain a global `_registry: Optional[SkillRegistry]` accessible via `get_skill_registry()`, initialized once via `init_skill_registry()` during application startup.

#### Scenario: First call initializes
- **WHEN** `init_skill_registry()` is called for the first time
- **THEN** registry scans skills/ and skills_custom/, compiles all patterns, sets global singleton

#### Scenario: Subsequent calls return cached
- **WHEN** `get_skill_registry()` is called after initialization
- **THEN** returns the same global instance

#### Scenario: Hot-add skill
- **WHEN** `registry.add_skill(config)` is called for newly created custom skill
- **THEN** config is registered, patterns recompiled, immediately matchable

### Requirement: Prompt fragment aggregation
The system SHALL provide `get_prompt_fragments(skill_names: List[str]) -> str` that concatenates prompt_fragment from multiple skills with double-newline separator.

#### Scenario: Single skill fragment
- **WHEN** get_prompt_fragments(["query-order-search"])
- **THEN** returns that skill's prompt_fragment string

#### Scenario: Multiple skills
- **WHEN** get_prompt_fragments(["skill-a", "skill-b"])
- **THEN** returns "fragment-a\n\nfragment-b"

#### Scenario: Unknown skill skipped
- **WHEN** get_prompt_fragments(["unknown"])
- **THEN** returns empty string
