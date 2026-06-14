# Skill 编写指南

> 适用对象：需要新增或修改 Skill 的开发者
> 关联设计文档：[design-skill-plan-c.md](design-skill-plan-c.md)

## 1. 概念

**Skill** 是对一组相关业务能力的封装：
- 一个意图匹配规则（用户说啥触发这个 skill）
- 一组可用工具（依赖 MCP/ERP 已注册的工具）
- 一段 prompt 片段（注入 system prompt 引导 LLM）
- 可选的工作流（preset 用 Python handler；custom 用 YAML）

| 类型 | 路径 | handler.py | 工作流定义位置 |
|------|------|------------|----------------|
| preset | `skills/{name}/` | ✅ 可选 | `skill.yaml` 的 `workflow.handler` 或 `workflow.steps` |
| custom | `skills_custom/{name}/` | ❌ 禁止 | `skill.yaml` 的 `workflow.steps`（仅 YAML） |

## 2. skill.yaml 字段

```yaml
name: my-skill                # 必填，kebab-case，全局唯一
version: "1.0"                # 可选，默认 "1.0"
description: "..."             # 必填，描述用途
category: preset              # preset | custom

intent_patterns:              # 必填，至少一种语言
  zh: ["改.*地址", "修改.*收货"]
  en: ["change.*address"]

tools:                        # 必填，依赖的 MCP/ERP 工具
  - query_order
  - update_order

prompt_fragment: |            # 可选，注入 system prompt
  修改地址时请先确认当前地址再操作。

workflow: null                # 无工作流（仅 prompt 注入）
# 或
workflow:
  handler: "handler.OrderEditAddressHandler"  # preset only
  steps:                                    # custom 用 YAML
    - id: step1
      type: tool_call
      tool: query_order
      params:
        order_id: "{{message}}"
```

## 3. handler.py 模板（preset 专用）

```python
"""My skill handler — bridge contract per skill-approval-bridge spec."""
from app.skills.base import SkillHandler, WorkflowResult, WorkflowStep


class MySkillHandler(SkillHandler):
    skill_name = "my-skill"

    def execute(self, message: str, context: dict) -> WorkflowResult:
        # DO NOT import app.approval_core
        # Use intermediate_data to pass approval contract
        if need_user_approval:
            return WorkflowResult(
                success=True,
                need_approval=True,
                intermediate_data={
                    "tool": "update_order",                      # 必填
                    "tool_args": {"order_id": "ORD-001"},       # 必填
                    "approval_summary": "修改订单 ORD-001",     # 必填
                },
            )
        if need_more_user_input:
            return WorkflowResult(
                success=True,
                need_more_info=True,
                intermediate_data={"current": "..."},
            )
        return WorkflowResult(success=True, intermediate_data={...})
```

**关键约束**：
- ❌ 不得 `import app.approval_core`
- ❌ 不得 `import app.agent`
- ✅ 通过 `intermediate_data` 传递意图，让 agent 层桥接

## 4. YAML 工作流步骤类型

| type | 字段 | 说明 |
|------|------|------|
| `tool_call` | `tool`, `params`, `output?`, `iterate?` | 调 MCP/ERP 工具 |
| `prompt` | `instruction` | 记录指令，LLM 后续处理 |

### 变量引用语法

```yaml
- id: parse
  type: prompt
  instruction: "从用户消息提取订单号"

- id: query
  type: tool_call
  tool: query_order
  params:
    order_id: "{{parse.items[*].order_id}}"   # 迭代引用
  iterate: true
  output: results

- id: summary
  type: prompt
  instruction: "汇总 {{results}} 为表格"
```

支持的引用：
- `{{message}}` — 用户原始消息
- `{{step_id.field}}` — 引用指定步骤输出的字段
- `{{step_id.items[*].field}}` — 配合 `iterate: true` 的数组字段

## 5. custom skill 安全约束

`SkillValidator._validate_security` 对以下文本做黑名单扫描：
- `description` / `prompt_fragment` / `workflow.steps[].instruction`

禁止关键词：
- **文件 IO**: `read file`, `write file`, `读文件`, `写文件`, `文件读写`
- **HTTP**: `http call`, `调用 http`, `fetch api`, `调用接口`
- **代理**: `proxy`, `转发`, `代理`
- **代码执行**: `exec`, `eval`, `subprocess`, `os.system`
- **动态 import**: `import`, `from X import`

违规返回 400 + 错误详情。

## 6. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills/available` | 列出所有已注册 skill |
| GET | `/api/skills/loaded` | 列出已加载 skill（Phase 1/2 同 available） |
| POST | `/api/skills/load` | 按需加载（Phase 1/2 预留） |
| POST | `/api/skills/validate` | 校验 custom skill 配置 |
| POST | `/api/skills/create` | 创建 custom skill（写盘 + 热加载） |

## 7. 调试清单

- Skill 未匹配：检查 `intent_patterns` 正则，用 `r.get_all_skills()` 验证加载
- handler 未加载：检查 `workflow.handler` 路径，**模块名必须匹配 .py 文件名**（如 `handler.OrderEditAddressHandler` 对应 `handler.py`）
- 工具调用失败：检查 `tools:` 是否在 `client_factory.get_all_tools()` 中
- custom skill 创建被拒：检查名称正则 `^[a-zA-Z0-9_-]+$`、description 非空、tools 存在、安全关键词
