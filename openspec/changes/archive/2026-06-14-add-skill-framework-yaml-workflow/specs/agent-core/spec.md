## ADDED Requirements

### Requirement: Skill matching priority
The agent loop SHALL call `SkillRegistry.match_skill(message)` before `intent_detector.detect_tool_intent()`. When a skill is matched, the agent enters the Skill execution path and SHALL NOT call `detect_tool_intent()` or `_force_tool_retry()`. When no skill is matched, the agent falls back to the existing `detect_tool_intent()` flow.

#### Scenario: Skill matched takes priority
- **WHEN** user sends "查一下订单 ORD-001 状态" and the query-order-search skill's intent pattern matches
- **THEN** agent enters Skill path (injects prompt_fragment, runs executor)
- **AND** detect_tool_intent is NOT called

#### Scenario: No skill matched falls back
- **WHEN** user sends a message that matches no skill's intent patterns
- **THEN** agent calls detect_tool_intent and proceeds with the existing tool-call flow

#### Scenario: Skill matched but execution fails
- **WHEN** skill is matched and SkillExecutor returns WorkflowResult(success=False)
- **THEN** agent returns SKILL_EXECUTION_FAILED error
- **AND** does NOT fall back to detect_tool_intent (no forced tool retry)

### Requirement: Skill execution routing
When a skill is matched, the agent SHALL route execution based on the executor result: (1) `success=True` with no flags → return results to user, (2) `need_approval=True` → call `_handle_skill_approval` bridge, (3) `need_more_info=True` → inject `intermediate_data` into system prompt and re-call LLM without tools.

#### Scenario: Skill success returns results
- **WHEN** SkillExecutor returns WorkflowResult(success=True, steps=[...], intermediate_data={...})
- **THEN** agent returns the workflow's intermediate_data as the tool_calls and runs LLM for final reply

#### Scenario: Skill need_approval routes to bridge
- **WHEN** SkillExecutor returns WorkflowResult(need_approval=True, intermediate_data={tool, tool_args, approval_summary})
- **THEN** agent calls `_handle_skill_approval(workflow_result, messages, logger)` which uses approval_core.create_pending

#### Scenario: Skill need_more_info injects context
- **WHEN** SkillExecutor returns WorkflowResult(need_more_info=True, intermediate_data={...})
- **THEN** agent appends system message describing skill state, then calls LLM without tools parameter
- **AND** returns LLM reply as user-facing response
