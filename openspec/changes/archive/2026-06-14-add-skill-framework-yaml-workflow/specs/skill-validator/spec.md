## Purpose

Define the Skill configuration validator: basic field checks, workflow step type validation, tool availability verification against the active client_factory, and custom-skill-specific security blacklists.

## ADDED Requirements

### Requirement: Basic field validation
The system SHALL validate that skill configuration contains non-empty `name` and `description` fields, and at least one of `intent_patterns.zh` or `intent_patterns.en` is a non-empty list.

#### Scenario: Missing name rejected
- **WHEN** config_data has empty or missing name
- **THEN** validator returns errors=["Skill 名称不能为空"]

#### Scenario: Missing description rejected
- **WHEN** config_data has empty or missing description
- **THEN** validator returns errors=["Skill 描述不能为空"]

#### Scenario: No intent patterns rejected
- **WHEN** both intent_patterns.zh and intent_patterns.en are empty lists
- **THEN** validator returns errors=["至少需要定义一种语言的意图匹配规则"]

#### Scenario: Tools list required
- **WHEN** tools is empty or missing
- **THEN** validator returns errors=["Skill 必须声明依赖的工具列表"]

### Requirement: Tool availability check
The system SHALL verify each tool declared in `tools:` exists in the provided `available_tools` list, where `available_tools` is the list of tool names extracted from `client_factory.get_all_tools()` with `mcp_` prefix stripped.

#### Scenario: Tool available
- **WHEN** tools: [query_order] and query_order is in available_tools
- **THEN** validator does not report this tool as missing

#### Scenario: Tool not registered
- **WHEN** tools: [nonexistent_tool] and nonexistent_tool is not in available_tools
- **THEN** validator returns errors=[f"工具 'nonexistent_tool' 未在当前 MCP 注册表中，可选工具: {available_tools}"]

#### Scenario: MCP prefix stripped
- **WHEN** client_factory returns tool named mcp_query_order and tools: [query_order]
- **THEN** validator strips prefix and matches successfully

### Requirement: Workflow step type validation
The system SHALL validate that each step in `workflow.steps` has `type` field with value `tool_call` or `prompt`, and required fields per type.

#### Scenario: tool_call step validated
- **WHEN** step has type=tool_call, tool=query_order, params={order_id: "123"}
- **THEN** validator checks tool exists in available_tools and params is non-empty dict

#### Scenario: prompt step validated
- **WHEN** step has type=prompt with non-empty instruction
- **THEN** validator passes

#### Scenario: Invalid type rejected
- **WHEN** step has type="unknown_type"
- **THEN** validator returns errors=[f"步骤 '{id}' 类型无效: unknown_type，仅支持 tool_call 和 prompt"]

#### Scenario: tool_call missing tool
- **WHEN** step has type=tool_call without tool field
- **THEN** validator returns errors=[f"步骤 '{id}' 缺少 tool 字段"]

### Requirement: Python handler disabled for custom skills
The system SHALL reject custom skills (category="custom") that declare `workflow.handler`, since custom skills must use YAML workflow only.

#### Scenario: Custom with handler rejected
- **WHEN** category="custom" and workflow.handler is non-null
- **THEN** validator returns errors=["自定义 Skill 不允许使用 Python handler，只能使用 YAML 工作流"]

#### Scenario: Preset with handler allowed
- **WHEN** category="preset" and workflow.handler is set
- **THEN** validator passes this check

### Requirement: Custom skill security blacklist
The system SHALL scan custom skill text content (`description`, `prompt_fragment`, `workflow.steps[].instruction`) against a blacklist of high-risk operation keywords: `file` (read/write), `http`/`fetch`/`request`/`api` (call), `forward`/`proxy`, `exec`/`eval`/`subprocess`/`os.`, `import`/`from X import`.

#### Scenario: File operation keyword rejected
- **WHEN** prompt_fragment contains "读取文件"
- **THEN** validator returns errors=[security violation message]

#### Scenario: HTTP call keyword rejected
- **WHEN** workflow.steps[0].instruction contains "调用 http 接口"
- **THEN** validator returns errors=[security violation message]

#### Scenario: Code execution keyword rejected
- **WHEN** description contains "exec subprocess"
- **THEN** validator returns errors=[security violation message]

#### Scenario: Preset skill exempt
- **WHEN** category="preset"
- **THEN** security blacklist is not applied

### Requirement: Skill directory integrity
The system SHALL provide `validate_skill_dir(skill_dir, is_custom)` that checks for `skill.yaml` presence and (for custom) absence of `handler.py`.

#### Scenario: Missing skill.yaml
- **WHEN** skill_dir lacks skill.yaml
- **THEN** validator returns (False, ["缺少 skill.yaml 配置文件"])

#### Scenario: Custom skill with handler.py rejected
- **WHEN** is_custom=True and handler.py exists in skill_dir
- **THEN** validator returns (False, ["自定义 Skill 不允许包含 handler.py 代码文件"])

#### Scenario: Preset skill with handler.py allowed
- **WHEN** is_custom=False and handler.py exists
- **THEN** validator passes directory check
