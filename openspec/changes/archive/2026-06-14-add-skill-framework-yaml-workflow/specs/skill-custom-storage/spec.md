## Purpose

Define the persistence location for custom skills: a flat directory `skills_custom/` at project root, sibling to `skills/` (preset), with `.gitignore` exclusion. Custom skills contain only `skill.yaml` (no handler.py, no workflow.md).

## ADDED Requirements

### Requirement: Custom skill directory path
The system SHALL persist custom skills at `_PROJECT_ROOT/skills_custom/{name}/skill.yaml` where `_PROJECT_ROOT` is the directory containing `app/` (resolved at runtime via `Path(__file__).resolve().parents[2]`).

#### Scenario: Path computation
- **WHEN** project root is `/workspace/erp-mvp-agent` and skill name is "batch-query-order"
- **THEN** custom skill yaml path is `/workspace/erp-mvp-agent/skills_custom/batch-query-order/skill.yaml`

#### Scenario: Different from preset path
- **WHEN** preset skill at `skills/query-order-search/skill.yaml` and custom at `skills_custom/batch-query-order/skill.yaml`
- **THEN** two paths are siblings under project root, NOT nested (preset/custom/...)

### Requirement: Flat directory structure
The system SHALL treat `skills_custom/` as a flat directory of skill subdirectories; no further nesting (no per-agent, per-user, or per-environment subdirectories in this change).

#### Scenario: One level deep
- **WHEN** custom skill "my-skill" exists
- **THEN** path is `skills_custom/my-skill/skill.yaml` — no `skills_custom/users/alice/my-skill/`

### Requirement: Custom skill contains only skill.yaml
The system SHALL enforce that custom skill directories contain only `skill.yaml`; no `handler.py`, no `workflow.md`, no other executable files.

#### Scenario: Only skill.yaml allowed
- **WHEN** creating custom skill via /api/skills/create
- **THEN** system writes ONLY skill.yaml to the directory

#### Scenario: handler.py rejected on validation
- **WHEN** validator.validate_skill_dir finds handler.py in custom skill_dir
- **THEN** returns (False, ["自定义 Skill 不允许包含 handler.py 代码文件"])

### Requirement: .gitignore rule
The system SHALL add `skills_custom/` to `.gitignore` so that user-created custom skills are not committed to version control.

#### Scenario: Gitignore entry
- **WHEN** `.gitignore` is updated
- **THEN** contains a line `skills_custom/` (or `skills_custom/*` with `!.gitkeep`)

#### Scenario: Custom skill not in git
- **WHEN** `git status` is run after creating custom skill
- **THEN** the new file under skills_custom/ is NOT shown as untracked

### Requirement: Custom skill reload on startup
The system SHALL scan `skills_custom/` on every application startup (same as `skills/`), loading all existing custom skills into the registry.

#### Scenario: Existing custom skill loaded
- **WHEN** `skills_custom/batch-query-order/skill.yaml` exists at startup
- **THEN** registry contains "batch-query-order" with all its config

#### Scenario: Missing skills_custom directory
- **WHEN** `skills_custom/` does not exist
- **THEN** loader logs warning and proceeds with empty custom dict (no error raised)

### Requirement: Hot-reload after create
The system SHALL immediately add newly created custom skills to the running registry via `registry.add_skill(config)` after writing the skill.yaml file, without requiring server restart.

#### Scenario: Create + immediate match
- **WHEN** POST /api/skills/create with name="my-skill" succeeds
- **THEN** next user message matching my-skill's intent_patterns is routed to my-skill in the same process

#### Scenario: add_skill recompiles patterns
- **WHEN** registry.add_skill(config) is called
- **THEN** `_compile_all_patterns()` re-runs and includes the new skill's patterns
