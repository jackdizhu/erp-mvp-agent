# Tasks: skill-workflow-yaml

> 对应 spec: [skill-workflow-yaml](../specs/skill-workflow-yaml/spec.md)
> 覆盖原 tasks.md 组 6（Python handler only）+ 组 11（YAML workflow 扩展）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/executor.py` | 新建 | ~180 | `SkillExecutor` + 4 个私有方法（YAML + 变量 + 迭代） |

---

## 1. `app/skills/executor.py` — 基础结构

### 1.1 SkillExecutor 类
- [ ] 1.1.1 定义 `class SkillExecutor:`
- [ ] 1.1.2 实现 `def execute(self, skill: SkillConfig, message: str, context: dict, available_tools: List[str] = None) -> Optional[WorkflowResult]:`
- [ ] 1.1.3 优先级路由（spec: 决策 4）：
  1. `skill.has_handler()` 为真 → 调 `_execute_handler`
  2. `skill.has_yaml_workflow()` 为真 → 调 `_execute_yaml_workflow`
  3. 否则 → `return None`（prompt 注入模式）

### 1.2 Python handler 分支
- [ ] 1.2.1 实现 `def _execute_handler(self, skill, message, context) -> Optional[WorkflowResult]:`
- [ ] 1.2.2 `try: result = skill.handler.execute(message, context)` 返回 result
- [ ] 1.2.3 `except Exception as e: return WorkflowResult(success=False, error=str(e))`
- [ ] 1.2.4 关键点：handler 抛异常不传播，包装为 `success=False` WorkflowResult

---

## 2. YAML 工作流执行

### 2.1 主流程
- [ ] 2.1.1 实现 `def _execute_yaml_workflow(self, steps: List[Dict], message: str, context: dict, available_tools: List[str]) -> WorkflowResult:`
- [ ] 2.1.2 初始化 `steps_result = []` 与 `step_outputs = {"message": message}`
- [ ] 2.1.3 顺序遍历 `steps`，按 `step["type"]` 分支
- [ ] 2.1.4 工具调用失败立即返回 `success=False`
- [ ] 2.1.5 全部完成返回 `WorkflowResult(success=True, steps=steps_result, intermediate_data=step_outputs)`

### 2.2 tool_call 步骤
- [ ] 2.2.1 获取 `raw_params = step_def.get("params", {})`
- [ ] 2.2.2 调 `_resolve_params(raw_params, step_outputs)` 得到 `resolved_params`
- [ ] 2.2.3 若 `step_def.get("iterate", False)` → 调 `_execute_iterative`（spec: D8 变量引用 + iterate）
- [ ] 2.2.4 否则调 `client_factory.execute_tool(step_def["tool"], resolved_params)`
- [ ] 2.2.5 异常时追加失败 `WorkflowStep` 到 `steps_result`，返回 `success=False`
- [ ] 2.2.6 成功后追加 `WorkflowStep(id=step_id, tool=..., result=..., status="completed")`
- [ ] 2.2.7 若 `step_def.get("output")` 存在 → `step_outputs[output_var] = result`

### 2.3 prompt 步骤
- [ ] 2.3.1 追加 `WorkflowStep(id=step_id, tool="prompt", status="completed", result={"instruction": step_def.get("instruction", "")})`
- [ ] 2.3.2 **不**调用任何 tool，不修改 `step_outputs`
- [ ] 2.3.3 关键点：prompt 步骤只记录指令，由 LLM 后续处理

### 2.4 变量引用解析（spec: D8）
- [ ] 2.4.1 实现 `def _resolve_params(self, params: Dict, step_outputs: Dict) -> Dict:`
- [ ] 2.4.2 递归遍历 dict：string 值调 `_replace_variables`；嵌套 dict 递归；其他原样返回
- [ ] 2.4.3 实现 `def _replace_variables(self, template: str, step_outputs: Dict) -> str:`
- [ ] 2.4.4 正则 `r'\{\{(.+?)\}\}'` 匹配
- [ ] 2.4.5 `var_path = "message"` → 返回 `step_outputs.get("message", "")`
- [ ] 2.4.6 `var_path = "step_id.path"` → `parts = var_path.split(".", 1)` 调 `_get_nested(step_outputs[step_id], path)`
- [ ] 2.4.7 缺失变量返回**空字符串**（不抛异常）
- [ ] 2.4.8 实现 `def _get_nested(self, data: Any, path: str) -> str:` 处理 `[*]` 剥离、`.` 分割、dict.get / list 索引

### 2.5 迭代执行（spec: iterate: true）
- [ ] 2.5.1 实现 `def _execute_iterative(self, step_id: str, tool: str, params: Dict, client_factory) -> List:`
- [ ] 2.5.2 遍历 `params` 找 list 值
- [ ] 2.5.3 对每个元素：`item_params = {k:v for k,v in params.items() if k != key}` + `item_params[key.rstrip("s")] = item`（单数化 key）
- [ ] 2.5.4 调 `client_factory.execute_tool(tool, item_params)` 收集到 `results`
- [ ] 2.5.5 单次失败不中断：该元素结果为 `{"error": str(e)}` 继续后续
- [ ] 2.5.6 非 list 参数 → 退化为单次调用

### 2.6 单元测试
- [ ] 2.6.1 Mock `client_factory` 验证 `tool_call` 步骤被正确调用
- [ ] 2.6.2 验证变量引用 `{{step_id.field}}` 正确解析
- [ ] 2.6.3 验证 `iterate: true` 触发 3 次调用（参数为 list of 3）
- [ ] 2.6.4 验证 prompt 步骤不调 tool
- [ ] 2.6.5 验证工具异常时返回 `success=False` + 失败步骤
- [ ] 2.6.6 验证缺失变量返回空字符串（不抛异常）
