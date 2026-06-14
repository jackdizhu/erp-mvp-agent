## Purpose

Define the YAML workflow executor: parsing `workflow.steps` from skill.yaml, executing `tool_call` and `prompt` step types, resolving `{{step_id.field}}` / `{{step_id.items[*].field}}` / `{{message}}` variable references in params, and supporting `iterate: true` for batch operations.

## ADDED Requirements

### Requirement: Execution priority routing
The system SHALL execute skills in this priority: (1) Python handler if `has_handler()` returns True, (2) YAML workflow steps if `has_yaml_workflow()` returns True, (3) None for prompt-injection-only skills.

#### Scenario: Handler takes precedence
- **WHEN** skill has both Python handler and workflow.steps
- **THEN** executor calls handler.execute() and returns its WorkflowResult

#### Scenario: YAML workflow when no handler
- **WHEN** skill has workflow.steps but no handler
- **THEN** executor parses steps and runs them sequentially

#### Scenario: No workflow returns None
- **WHEN** skill has neither handler nor workflow.steps
- **THEN** executor returns None (LLM handles via prompt only)

### Requirement: tool_call step execution
The system SHALL execute `tool_call` steps by resolving variable references in `params` and calling `client_factory.execute_tool(tool, params)`, storing the result in `step_outputs[output_var]`.

#### Scenario: Simple tool call
- **WHEN** step type=tool_call, tool=query_order, params={order_id: "123"}
- **THEN** executor calls client_factory.execute_tool("query_order", {order_id: "123"}) and stores result in step_outputs[output_var]

#### Scenario: Variable reference resolved
- **WHEN** step params has order_id: "{{parse_input.items[0].order_id}}" and step_outputs["parse_input"] = {items: [{order_id: "ORD-001"}]}
- **THEN** resolved params has order_id: "ORD-001"

#### Scenario: Tool call failure aborts workflow
- **WHEN** client_factory.execute_tool raises exception
- **THEN** executor returns WorkflowResult(success=False, error=f"步骤 '{id}' 执行失败: {e}", steps=[failed_step])

### Requirement: prompt step recording
The system SHALL record `prompt` steps with their `instruction` text in `steps_result` and **not** call any tool; LLM consumes the instruction on next generation round.

#### Scenario: Prompt step recorded
- **WHEN** step type=prompt with instruction="从用户消息中提取所有订单号"
- **THEN** WorkflowStep(id=step_id, tool="prompt", status="completed", result={"instruction": "..."}) is added to steps

#### Scenario: Prompt step not executed as tool
- **WHEN** step type=prompt
- **THEN** client_factory.execute_tool is NOT called

### Requirement: Variable reference resolution
The system SHALL resolve `{{...}}` patterns in string param values using `_replace_variables()`: split into `step_id.path`, look up in `step_outputs`, navigate nested dict/list via `[*]` strip + dot split.

#### Scenario: message reference
- **WHEN** params has content: "{{message}}"
- **THEN** resolved value is step_outputs["message"] (original user message)

#### Scenario: Nested field reference
- **WHEN** step_outputs["parse_input"] = {order_id: "ORD-001", items: [{order_id: "ORD-002"}]} and params has "{{parse_input.order_id}}"
- **THEN** resolved value is "ORD-001"

#### Scenario: Iterator field reference
- **WHEN** step_outputs["parse_input"] = {items: [{order_id: "A"}, {order_id: "B"}]} and params has "{{parse_input.items[*].order_id}}"
- **THEN** resolved value is "A" (first item's field; iterate mode uses this for each iteration)

#### Scenario: Missing variable returns empty string
- **WHEN** params references non-existent step_id
- **THEN** resolved value is empty string (no exception raised)

### Requirement: Iterative execution
The system SHALL support `iterate: true` on `tool_call` steps by detecting array values in resolved params, then calling the tool once per array element with the singular key name (strip trailing "s").

#### Scenario: Iterate over list
- **WHEN** step has iterate=true, resolved params = {order_id: ["A", "B", "C"]}
- **THEN** executor calls query_order({order_id: "A"}), query_order({order_id: "B"}), query_order({order_id: "C"}) and aggregates results as list

#### Scenario: Non-iterate falls through
- **WHEN** step has iterate=true but params has scalar value
- **THEN** executor makes a single tool call (treats as list of one)

#### Scenario: Per-iteration error captured
- **WHEN** iterating and one call fails
- **THEN** that iteration's result is {"error": "..."} but other iterations continue

### Requirement: YAML workflow returns aggregate WorkflowResult
The system SHALL return WorkflowResult(success=True, steps=steps_result, intermediate_data=step_outputs) after all steps complete.

#### Scenario: All steps succeed
- **WHEN** all steps complete without exception
- **THEN** WorkflowResult has success=True and full step history

#### Scenario: Step failure propagates
- **WHEN** any step raises exception
- **THEN** WorkflowResult has success=False, error message, and steps up to failure
