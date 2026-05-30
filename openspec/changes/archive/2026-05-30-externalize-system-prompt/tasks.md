## 1. Configuration Files

- [x] 1.1 Create `app/config/prompts.yaml` with prompt templates
- [x] 1.2 Update `app/config/__init__.py` to export `load_prompts` function

## 2. Prompt Config Module

- [x] 2.1 Create `app/prompt_config.py` with `load_prompts()` function
- [x] 2.2 Implement `build_capabilities_list()` function from TOOL_SCHEMAS
- [x] 2.3 Implement `build_system_prompt()` assembly function
- [x] 2.4 Add fallback values for missing/invalid config

## 3. Integration

- [x] 3.1 Update `app/llm.py` to import from `prompt_config` module
- [x] 3.2 Replace hardcoded `SYSTEM_PROMPT` with `build_system_prompt()` call
- [x] 3.3 Export `SYSTEM_PROMPT` as module-level constant for backward compatibility

## 4. Testing

- [x] 4.1 Test with valid `prompts.yaml` - verify prompt structure
- [x] 4.2 Test fallback behavior when YAML is missing
- [x] 4.3 Test fallback behavior when YAML is invalid
- [x] 4.4 Verify capability list matches TOOL_SCHEMAS descriptions
- [x] 4.5 End-to-end test: query order via chat
