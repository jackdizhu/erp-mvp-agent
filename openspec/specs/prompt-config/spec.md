# Prompt Configuration

## Purpose

Provide centralized, configurable system prompt management for the ERP agent. This enables runtime customization of prompts without code changes and supports dynamic capability enumeration from tool schemas.

## Requirements

### Requirement: YAML Configuration Loading
The system SHALL load prompt configuration from `app/config/prompts.yaml` file.

#### Scenario: Load valid YAML configuration
- **WHEN** system starts with valid `prompts.yaml` file
- **THEN** configuration SHALL be parsed successfully
- **AND** `load_prompts()` SHALL return dictionary with keys: role, risk_notice, response_style, capabilities_header

#### Scenario: Fallback on missing configuration
- **WHEN** `prompts.yaml` file does not exist
- **THEN** system SHALL use hardcoded fallback values
- **AND** system SHALL log warning message

#### Scenario: Fallback on invalid YAML
- **WHEN** `prompts.yaml` file exists but contains invalid YAML
- **THEN** system SHALL use hardcoded fallback values
- **AND** system SHALL log error message with parsing details

### Requirement: Dynamic Capability List Generation
The system SHALL generate capability list automatically from `erp_app/tools.py` TOOL_SCHEMAS.

#### Scenario: Generate capabilities from tool schemas
- **WHEN** `build_system_prompt()` is called
- **THEN** system SHALL extract all tool descriptions from TOOL_SCHEMAS
- **AND** format each as "- {description}" bullet point

#### Scenario: Empty tools list handling
- **WHEN** TOOL_SCHEMAS is empty
- **THEN** capability list SHALL be empty string
- **AND** system SHALL continue without error

### Requirement: System Prompt Assembly
The system SHALL assemble complete SYSTEM_PROMPT from configuration and dynamic content.

#### Scenario: Assemble complete prompt
- **WHEN** `build_system_prompt()` is called
- **THEN** output SHALL follow structure:
```
{role}

{capabilities_header}
- {tool_description_1}
- {tool_description_2}
...

{risk_notice}
{response_style}
```

#### Scenario: Exclude empty optional sections
- **WHEN** capabilities_footer is empty or not configured
- **THEN** system SHALL skip that section in final output

### Requirement: Prompt Configuration Structure
The YAML configuration SHALL support the following structure:

```yaml
system_prompt:
  role: "你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。"
  capabilities_header: "你可以执行以下操作："
  capabilities_footer: ""  # optional
  risk_notice: "对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。"
  response_style: "请用简洁专业的中文回复用户。"
```

#### Scenario: Load all configuration fields
- **WHEN** `prompts.yaml` contains all defined fields
- **THEN** `load_prompts()` SHALL return all values correctly parsed

#### Scenario: Support missing optional fields
- **WHEN** `prompts.yaml` is missing capabilities_footer
- **THEN** system SHALL use empty string as default value
- **AND** system SHALL NOT raise error