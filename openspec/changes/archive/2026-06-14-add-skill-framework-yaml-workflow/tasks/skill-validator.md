# Tasks: skill-validator

> 对应 spec: [skill-validator](../specs/skill-validator/spec.md)
> 覆盖原 tasks.md 组 5

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/validator.py` | 新建 | ~170 | `FORBIDDEN_PATTERNS` + `SkillValidator` 5 个方法 |

---

## 1. 模块级常量

### 1.1 FORBIDDEN_PATTERNS 黑名单
- [ ] 1.1.1 定义 `FORBIDDEN_PATTERNS: List[re.Pattern] = [...]`，每条 pattern 用 `re.IGNORECASE`
- [ ] 1.1.2 至少包含：`file.*read|文件.*读`（文件 IO）、`http.*call|api.*请求|fetch.*request`（HTTP）、`forward|proxy|转发|代理`（转发）、`exec|eval|subprocess|os\.`（代码执行）、`^import|^from\s+\w+\s+import`（动态导入）
- [ ] 1.1.3 关键约束：custom skill 才扫描，preset 跳过（spec: 决策 5 + D9）

---

## 2. `SkillValidator` 类

### 2.1 主入口
- [ ] 2.1.1 定义 `class SkillValidator:`
- [ ] 2.1.2 实现 `def validate_config(self, config_data: Dict, available_tools: List[str], is_custom: bool = True) -> Tuple[bool, List[str]]:` 返回 `(is_valid, errors)`
- [ ] 2.1.3 在方法内顺序执行：基础字段 → 意图规则 → 工具列表 → 工作流 → 安全校验
- [ ] 2.1.4 关键点：custom skill 多检查"handler 不允许"分支

### 2.2 基础字段校验
- [ ] 2.2.1 检查 `config_data["name"]` 非空（`errors.append("Skill 名称不能为空")`）
- [ ] 2.2.2 检查 `config_data["description"]` 非空
- [ ] 2.2.3 检查 `config_data.get("intent_patterns", {}).get("zh")` 或 `.get("en")` 至少一个非空 list
- [ ] 2.2.4 检查 `config_data.get("tools", [])` 非空 list

### 2.3 工具可用性校验
- [ ] 2.3.1 接收 `available_tools` 时**先**统一去 `mcp_` 前缀（与 `client_factory._mcp_tool_alias` 保持一致）
- [ ] 2.3.2 遍历 `config_data["tools"]`，每个工具必须在 `available_tools` 中
- [ ] 2.3.3 缺失时 `errors.append(f"工具 'xxx' 未在当前 MCP 注册表中，可选工具: {comma_separated}")`

### 2.4 工作流校验
- [ ] 2.4.1 实现 `def _validate_workflow(self, workflow: Dict, available_tools: List[str], is_custom: bool) -> List[str]:`
- [ ] 2.4.2 短路：如果 `workflow.get("handler")` 存在，跳过步骤严格校验（仅作参考）
- [ ] 2.4.3 否则检查 `workflow.get("steps", [])` 非空
- [ ] 2.4.4 遍历步骤调 `_validate_step` 累加错误
- [ ] 2.4.5 custom skill 检查 `workflow.get("handler")` 存在时**报错**：`"自定义 Skill 不允许使用 Python handler"`

### 2.5 步骤校验
- [ ] 2.5.1 实现 `def _validate_step(self, step: Dict, index: int, available_tools: List[str]) -> List[str]:`
- [ ] 2.5.2 检查 `step.get("type")` 必须是 `tool_call` 或 `prompt`，否则报错
- [ ] 2.5.3 `tool_call` 类型：检查 `step["tool"]` 存在且在 `available_tools` 中；检查 `step["params"]` 非空 dict
- [ ] 2.5.4 `prompt` 类型：检查 `step["instruction"]` 非空

### 2.6 安全校验
- [ ] 2.6.1 实现 `def _validate_security(self, config_data: Dict) -> List[str]:`
- [ ] 2.6.2 拼接文本：`description + " " + prompt_fragment + " " + " ".join(step["instruction"] for step in workflow.steps)`
- [ ] 2.6.3 用每条 `FORBIDDEN_PATTERNS` `re.search` 匹配，命中追加 `errors.append(f"安全校验失败：包含禁止的操作 '{match.group()}'...")`

### 2.7 目录完整性
- [ ] 2.7.1 实现 `def validate_skill_dir(self, skill_dir: Path, is_custom: bool = True) -> Tuple[bool, List[str]]:`
- [ ] 2.7.2 检查 `skill_dir / "skill.yaml"` 存在
- [ ] 2.7.3 custom 时检查 `handler.py` **不**存在，违反则报错

### 2.8 单元测试
- [ ] 2.8.1 测试正常 preset skill 通过
- [ ] 2.8.2 测试 custom skill 含 `handler.py` 被拒
- [ ] 2.8.3 测试 custom skill 含 `from foo import bar` 被安全规则拒
- [ ] 2.8.4 测试 tools 引用未注册工具被拒
- [ ] 2.8.5 测试 step type=`unknown` 被拒
