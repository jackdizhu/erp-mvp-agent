## Why

当前 `app/agent.py` 的意图识别完全依赖 `intent_detector.detect_tool_intent` 字符串正则匹配，复杂业务场景（如"修改订单收货地址"包含查→确认→改→验证的多步流程）需要工作流编排能力，而当前架构无 Skill 框架支持，扩展多 Agent、多 MCP、可自定义工作流时只能改代码。

需要新增 Skill 框架：preset skill 用 Python handler 编排工作流，custom skill 用 YAML 声明工作流（无需写代码），同时引入安全校验、工具可用性校验、Skill 管理 API，支持按需加载 custom skill 扩展能力。

## What Changes

- **新增** `app/skills/` 运行时模块（base / loader / registry / executor / validator 五个子模块），实现 Skill 的扫描加载、意图匹配、Python handler 与 YAML 工作流执行、安全校验
- **新增** `skills/` 顶层目录存放 preset skill 的 `skill.yaml` 配置与 `handler.py` Python 编排
- **新增** `skills_custom/` 顶层目录存放用户自定义 skill（扁平结构、`.gitignore` 忽略），仅含 `skill.yaml`（YAML 工作流）
- **修改** `app/llm.py`：删除模块级 `SYSTEM_PROMPT` 常量缓存，改为 `build_system_prompt(skill_fragments)` 动态注入
- **修改** `app/prompt_config.py`：`build_system_prompt` 新增 `skill_fragments: str = ""` 参数，拼接"=== 技能指引 ==="片段
- **修改** `app/agent.py`：集成 `SkillRegistry.match_skill`，在 chat/stream_chat 入口**优先**匹配 Skill（**不再兜底**调用 `detect_tool_intent`），失败直接返回 `SKILL_EXECUTION_FAILED`；新增 `_handle_skill_approval` 桥接函数处理 `need_approval=True` 的工作流结果
- **修改** `app/main.py`：startup 调 `init_skill_registry()`；新增 5 个 `/api/skills/*` 端点（available / loaded / load / validate / create）
- **新增** 错误码 `SKILL_EXECUTION_FAILED`
- **新增** 依赖 `pyyaml>=6.0`
- **新增** `.gitignore` 规则忽略 `skills_custom/`

## Capabilities

### New Capabilities

- `skill-runtime`: Skill 框架核心运行时 — `base.py` 数据结构（WorkflowStep/WorkflowResult/SkillHandler）、`loader.py` 扫描 `skills/` 与 `skills_custom/` 加载 skill.yaml、`registry.py` 意图正则匹配 + 全局单例 + 动态添加（热加载）
- `skill-validator`: Skill 校验器 — `validator.py` 实现基础字段、意图规则、工具可用性、custom skill 额外安全校验（禁止文件读写 / 接口调用 / 转发 / import 等高危关键词）
- `skill-workflow-yaml`: YAML 工作流执行器 — `executor.py` 支持 tool_call 与 prompt 两类步骤、参数变量引用 `{{step_id.field}}` / `{{step_id.items[*].field}}` / `{{message}}`、迭代执行（`iterate: true`）
- `skill-api`: Skill 管理 REST API — 5 个端点（`/api/skills/available`、`/api/skills/loaded`、`/api/skills/load`、`/api/skills/validate`、`/api/skills/create`），含 Pydantic 请求/响应模型
- `skill-approval-bridge`: Skill → 审批桥接 — handler 返回 `WorkflowResult(need_approval=True, intermediate_data={tool, tool_args, approval_summary})`，由 `agent.py` 调用 `approval_core.create_pending` 复用现有审批流，handler **不直接耦合** `approval_core`
- `skill-custom-storage`: Custom skill 持久化路径 — 扁平目录 `_PROJECT_ROOT/skills_custom/{name}/skill.yaml`（**不**使用嵌套 `skills/custom/`），整体 `.gitignore` 忽略
- `skill-system-prompt-dynamic`: 动态 System Prompt 注入 — `app/llm.py` 移除模块级 `SYSTEM_PROMPT` 常量；`agent.py` 每次构造 messages 时调用 `build_system_prompt(skill_fragments=...)` 拼接命中 skill 的 `prompt_fragment`
- `skill-failure-handling`: Skill 失败与需补充信息语义 — 执行失败 (`success=False`) **不兜底** `detect_tool_intent`，返回 `SKILL_EXECUTION_FAILED`；`need_more_info=True` 时把 `intermediate_data` 注入 system prompt 让 LLM 续谈

### Modified Capabilities

- `agent-core`: 意图识别增加 Skill 匹配优先级 — `agent.py` chat/stream_chat 入口先调 `SkillRegistry.match_skill`，命中后**跳过** `detect_tool_intent`；失败语义变更为返回 `SKILL_EXECUTION_FAILED` 而非兜底 tool retry
- `prompt-config`: `build_system_prompt` 新增可选 `skill_fragments: str = ""` 参数；命中 skill 时追加"=== 技能指引 ==="段落
- `chat-api`: 新增 5 个 `/api/skills/*` 端点（available/loaded/load/validate/create）
- `error-handling`: 新增错误码 `SKILL_EXECUTION_FAILED`（source="skill"，recoverable=true），用于 Skill 命中但执行失败场景
- `tool-system`: Skill 工作流的 `tool_call` 步骤复用 `client_factory.execute_tool`，MCP 工具名仍走 `_mcp_tool_alias` 别名解析；custom skill 工具可用性通过 `client_factory.get_all_tools()` 提取的短名校验

## Impact

- **后端新增文件**：
  - `app/skills/__init__.py`、`base.py`、`loader.py`、`registry.py`、`executor.py`、`validator.py`
  - `skills/query-order-search/skill.yaml`
  - `skills/query-order-edit-address/skill.yaml`、`handler.py`
  - `skills_custom/batch-query-order/skill.yaml`（示例 custom skill）
- **后端修改文件**：`app/llm.py`（删模块级 SYSTEM_PROMPT）、`app/prompt_config.py`（加 skill_fragments 参数）、`app/agent.py`（集成 Skill 匹配 + 桥接审批）、`app/main.py`（startup 初始化 + 5 个 API 端点）、`app/errors.py`（新增 `skill_execution_failed` 错误类型）
- **配置文件**：`.gitignore` 新增 `skills_custom/`
- **依赖**：`app/requirements.txt` 新增 `pyyaml>=6.0`
- **API 变更**：新增 5 个 `/api/skills/*` 端点，不影响现有 `/chat`、`/chat/stream`、`/chat/confirm`、`/api/approval/*` 行为
- **数据契约变更**：`WorkflowResult` 新增 `need_approval` / `need_more_info` / `intermediate_data` 字段约定（**handler 实现契约**，非 API 字段）
- **向后兼容**：未命中 Skill 时 `agent.py` 行为与现状等价（`detect_tool_intent` 兜底逻辑**保留**在"未命中 Skill"分支，**非**"命中 Skill 后失败"分支）
- **审批流程**：handler 不直接调 `approval_core`，通过 `intermediate_data` 传递 `tool` + `tool_args` + `approval_summary`，由 `agent.py` 桥接，与现有 DANGER 工具走同一 `create_pending` 路径
