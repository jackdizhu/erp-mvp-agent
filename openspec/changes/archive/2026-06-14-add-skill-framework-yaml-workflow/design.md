## Context

### 背景

`erp-mvp-agent` 当前为 **单 Agent + 单 MCP + 硬编码工具** 紧耦合架构，所有配置集中在 `app/config_dir/`：

- 意图检测：`app/intent_detector.py` 字符串正则匹配 `update_order` / `cancel_order` 等工具名
- 工具调用：`app/agent.py` chat 流中 LLM 自行调度，agent 仅做风险等级路由
- 工作流：硬编码在 `agent.py` 的 `_handle_tool_calls` / `_execute_caution` 中，无通用编排
- 提示词：`app/llm.py` 模块级常量 `SYSTEM_PROMPT = build_system_prompt()` 启动时固化

### 痛点

1. **多步业务流程硬编码**：如"修改收货地址"需"查询→确认→修改→验证"四步，扩展同类工作流需改 `agent.py`
2. **多 Agent 难支持**：意图规则、工具集、提示词全部耦合，单 Agent 架构无法满足只读查询、供应商专员等多角色
3. **Custom 扩展门槛高**：用户新增业务场景必须改 Python 代码 + 重启服务
4. **Prompt 缓存刚性**：模块级 `SYSTEM_PROMPT` 无法按会话/角色注入差异化片段

### 设计输入

- 上游文档：[docs/architecture-upgrade-agent-mcp-skill.md](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/docs/architecture-upgrade-agent-mcp-skill.md)（架构升级总览）
- 上游文档：[docs/design-skill-plan-c.md](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/docs/design-skill-plan-c.md)（方案 C：YAML 工作流 + Custom Skill）
- 上游文档：[docs/design-skill-plan-b.md](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/docs/design-skill-plan-b.md)（方案 B：Python handler 工作流）

方案 C 选定为本次实施版本：在 B 的基础上新增 YAML 工作流执行器 + custom skill 能力 + 安全校验。

## Goals / Non-Goals

**Goals:**

- 实现 Skill 框架运行时（base / loader / registry / executor / validator 五模块）
- 支持 preset skill（Python handler 工作流）+ custom skill（YAML 工作流）双模式
- 实现 Skill 意图匹配 + prompt 注入 + 工作流执行的完整链路
- 实现 5 个 Skill 管理 API（available / loaded / load / validate / create）
- 实现 custom skill 持久化（`skills_custom/` 扁平目录）
- 修复 `app/llm.py` 硬编码 `SYSTEM_PROMPT` 问题，改为动态注入
- 保持现有 `/chat` / `/chat/stream` / `/chat/confirm` 行为向后兼容

**Non-Goals:**

- 不实现多 Agent 体系（`agent/*.yaml`、会话绑定 Agent）—— 属于后续升级
- 不实现 MCP 多客户端切换 / 重载（已有 `mcp_registry`）—— 保持现状
- 不实现工作流可视化编辑器（前端）—— 仅提供后端 API
- 不实现条件分支 / 并行 / 嵌套工作流 —— 仅顺序执行 + 迭代
- 不实现 Skill 版本管理 / 回滚 —— custom skill 直接覆盖同名
- 不实现 custom skill 在前端表单的填写 UI —— 文档化字段，前端后续迭代

## Decisions

### D1. YAML 工作流定义嵌入 `skill.yaml`（**不**使用独立 `workflow.md`）

**决策**：工作流步骤直接写在 `skill.yaml` 的 `workflow.steps` 字段，不使用 `workflow_parser.py` 解析 Markdown DSL。

**替代方案**：
- ❌ workflow.md（方案 A 原版）：需维护 ~120 行 Markdown 解析器，规则严苛（`### N.` 标记步骤、`- 类型:` 固定字段、参数必须 JSON），用户学 DSL
- ❌ 独立 `workflow.json` 文件：与 `skill.yaml` 重复，扫描复杂度翻倍
- ✅ skill.yaml 内嵌 workflow.steps：YAML 自带 `yaml.safe_load` 解析和编辑器校验，零额外解析器

**理由**：YAML 比 Markdown DSL 更易学且工程支持更好；砍掉解析器减少维护成本；每个 Skill 只需一个 `skill.yaml` 文件。

### D2. `SYSTEM_PROMPT` 模块级缓存改为动态注入

**决策**：删除 `app/llm.py` 中的 `SYSTEM_PROMPT = build_system_prompt()` 模块级常量；`agent.py` 每次构造 messages 时调 `build_system_prompt(skill_fragments=...)`。

**替代方案**：
- ❌ 保留模块级 + 加 `set_system_prompt(fragments)` 全局 setter：线程不安全，多会话并发会串扰
- ❌ 用 `functools.lru_cache` 缓存：以 skill 名为 key 缓存，多 skill 组合（fragment 拼接）会失效
- ✅ 动态注入：每次 chat 调用拼装一次，约 0.1-0.5ms 成本可接受

**理由**：方案 C 明确"按需加载"语义；动态注入是按需加载的前置条件。

### D3. 审批桥接由 `agent.py` 负责，handler 不直接调 `approval_core`

**决策**：`SkillHandler.execute()` 返回 `WorkflowResult(need_approval=True, intermediate_data={tool, tool_args, approval_summary})`；`agent.py` 检测该标志后调 `approval_core.create_pending(tool, tool_args, messages)`。

**替代方案**：
- ❌ handler 直接 `import app.approval_core`：handler 单元测试依赖 approval_core，难以纯函数测试
- ❌ executor 桥接：executor 只做执行，不应该承担 Agent 编排职责
- ✅ agent.py 桥接：handler 保持纯函数（输入 message+context → 输出 WorkflowResult），审批是 Agent 编排的一部分

**理由**：保持 handler 与 approval_core 解耦，handler 可独立测试；Agent 编排职责统一在 agent.py。

### D4. 意图匹配优先级：Skill 优先，**命中后不调用** `detect_tool_intent`

**决策**：`agent.py` chat/stream_chat 入口先调 `SkillRegistry.match_skill`；命中则**直接进入 Skill 路径**，不再调用 `detect_tool_intent`。

**替代方案**：
- ❌ Skill 与 detect_tool_intent 并行匹配，谁先命中用谁：可能出现 Skill 命中 query-order-search 同时 detect_tool_intent 命中 update_order 的歧义
- ❌ detect_tool_intent 优先：违背"业务工作流优先于原始工具调用"的设计意图
- ✅ Skill 优先：业务意图高于工具意图

**理由**：Skill 是对工具的业务封装，匹配 Skill 后 LLM 应在 Skill 的 prompt 引导下工作，绕过 detect_tool_intent 避免强制 tool retry 干扰 Skill 流程。

### D5. Custom skill 持久化路径：`skills_custom/{name}/skill.yaml` 扁平

**决策**：custom skill 写入 `_PROJECT_ROOT/skills_custom/{name}/skill.yaml`，**不**使用方案 C 文档中的 `skills/custom/{name}/skill.yaml` 嵌套结构。

**替代方案**：
- ❌ 嵌套 `skills/custom/`：与 preset 同仓库但多层，`.gitignore` 规则需精确到子目录
- ✅ 扁平 `skills_custom/`：与 preset 同级，`.gitignore` 一行 `skills_custom/` 整体忽略

**理由**：扁平结构更易管理；custom 不入库（动态创建），扁平路径与"自定义临时数据"语义匹配。

### D6. Skill 执行失败不兜底 `detect_tool_intent`

**决策**：`WorkflowResult.success=False` 时直接返回 `SKILL_EXECUTION_FAILED` 错误，**不**自动回退到 `detect_tool_intent` 强制 tool retry。

**替代方案**：
- ❌ 失败兜底：可能误调 `update_order` 等 DANGER 工具，绕过 Skill 的业务约束
- ✅ 不兜底：失败信息透明返回给用户，用户可换说法或重试

**理由**：避免 Skill 失败时静默调用高危工具；保留"Skill 优先"的强语义。

### D7. `need_more_info=True` 时 `intermediate_data` 注入 system prompt

**决策**：handler 返回 `need_more_info=True` 时，`agent.py` 把 `intermediate_data` 拼接到 system prompt 末尾，调 LLM（**不**注入 tools）生成追问回复。

**替代方案**：
- ❌ 直接把 `intermediate_data` 作为 user message：语义错位（这是系统状态而非用户输入）
- ❌ 调工具继续执行：handler 已声明需要更多参数，再调工具可能误用默认值
- ✅ system prompt 注入：保留语义清晰，LLM 基于已执行步骤结果生成追问

**理由**：让 LLM 看到"我已经查了订单 ORD-001 当前地址是上海xxx"等上下文，自然生成"请告诉我要改成什么？"

### D8. 变量引用语法：`{{step_id.field}}` / `{{step_id.items[*].field}}` / `{{message}}`

**决策**：YAML 工作流步骤 `params` 中字符串值支持三种变量引用，**不**支持复杂表达式（如算术、函数调用）。

**语法**：
```yaml
- id: batch_query
  type: tool_call
  tool: query_order
  params:
    order_id: "{{parse_input.items[*].order_id}}"   # 迭代引用
```

**理由**：限制边界，避免实现表达式引擎；id-based 引用比序号引用更稳定（步骤顺序调整不会破坏引用）。

### D9. Custom skill 安全校验：黑名单正则扫描

**决策**：[validator.py](../specs/skill-validator/spec.md) 对 custom skill 的 `description` / `prompt_fragment` / `workflow.steps[].instruction` 文本做正则黑名单匹配，禁止关键词：`file` / `http` / `forward` / `exec` / `import` 等。

**替代方案**：
- ❌ 白名单（仅允许某些动词）：过度限制，YAML 工作流的核心价值是"灵活编排"，白名单会破坏灵活性
- ✅ 黑名单：限制已知高危操作，允许大部分编排场景

**已知缺陷**：正则不够严密（如 `r'(?:file|文件)'` 单独命中即报错），后续需持续维护词库。

### D10. MCP 工具名校验：去 `mcp_` 前缀

**决策**：`validator.validate_config` 接收 `available_tools` 时统一去 `mcp_` 前缀，与 `client_factory._mcp_tool_alias` 映射保持一致。

**理由**：skill.yaml 中声明 `tools: - query_order`（业务短名），而 `client_factory.get_all_tools()` 返回的可能是 `mcp_query_order`（带前缀），校验时需统一。

## Risks / Trade-offs

| # | 风险 / 权衡 | 影响 | 缓解 |
|---|------------|------|------|
| R1 | 动态 SYSTEM_PROMPT 性能开销 | 低：~0.1-0.5ms/次 | 接受；`build_system_prompt` 内部仅做字符串拼接，无 IO |
| R2 | Handler 动态 `importlib` 安全 | 中：handler 文件可执行任意 Python | 仅加载 `skills/`（preset）目录下的 handler；custom skill 禁止 `handler.py`（目录扫描时跳过） |
| R3 | YAML 工作流变量引用解析复杂 | 中：嵌套路径、迭代、缺失字段边界多 | 文档明确"仅支持简单引用和迭代"；解析失败返回原值（不抛异常） |
| R4 | Custom skill 热加载覆盖风险 | 低：同名 skill 后注册覆盖前者 | `registry.add_skill` 后注册覆盖；`/api/skills/create` 创建前检查重名（`get_skill(name) is None`） |
| R5 | 黑名单正则误杀 / 漏判 | 中：可能误禁合法 skill 或漏掉变种高危词 | 词库持续维护；后续可升级为 AST 分析 + 沙箱执行 |
| R6 | Skill 失败不兜底导致用户感知差 | 低：失败时报错不友好 | `SKILL_EXECUTION_FAILED` 错误携带 skill 名称与原始错误，前端可显示"技能 query-order-search 执行失败：xxx" |
| R7 | `need_more_info` 注入 system prompt 干扰 LLM | 低：intermediate_data 内容可能很长 | 限制注入数据量（`len(intermediate_data) < 2000` 字符），超出截断 |
| R8 | 5 个新 API 端点需前端配合才能发挥价值 | 中：暂无前端消费方 | 后端先实现，前端迭代对接 |
| R9 | Custom skill 持久化无版本管理 | 低：修改 skill.yaml 直接覆盖 | 接受；custom 是用户私有配置，不入版本库 |
| R10 | `pyyaml` 依赖新增 | 低：~1MB 安装包 | 必要依赖，无替代方案 |

## Migration Plan

### 阶段 1（向后兼容上线）

1. **新增模块**：`app/skills/{__init__,base,loader,registry,executor,validator}.py`（共 6 文件）
2. **新增数据**：`skills/query-order-search/skill.yaml`、`skills/query-order-edit-address/{skill.yaml, handler.py}`
3. **修改 `app/prompt_config.py`**：加 `skill_fragments` 参数
4. **修改 `app/agent.py`**：集成 Skill 匹配（**默认不开启**，需环境变量 `ENABLE_SKILL=true`）
5. **不修改 `app/llm.py`**：模块级 `SYSTEM_PROMPT` 暂保留，新增 `build_system_prompt(skill_fragments=...)` 兼容调用

此阶段：未命中 Skill 时行为与现状完全一致。

### 阶段 2（启用 Skill）

1. **修改 `app/llm.py`**：删除模块级 `SYSTEM_PROMPT` 常量
2. **修改 `app/agent.py`**：默认开启 Skill 匹配；启用 `_handle_skill_approval` 桥接
3. **修改 `app/main.py`**：startup 调 `init_skill_registry()`；新增 5 个 `/api/skills/*` 端点
4. **新增 `skills_custom/`** 示例：`skills_custom/batch-query-order/skill.yaml`

此阶段：Skill 框架完全启用，未命中 Skill 时仍走 `detect_tool_intent` 兜底。

### 回滚策略

- 阶段 1 回滚：删除 `app/skills/` 6 文件 + `skills/` 数据目录，`agent.py` 因 `ENABLE_SKILL` 默认 false 无影响
- 阶段 2 回滚：恢复 `app/llm.py` 模块级 `SYSTEM_PROMPT`；`agent.py` Skill 路径加 `if not ENABLE_SKILL: return old_path()`

## Open Questions

| # | 问题 | 候选方案 | 倾向 |
|---|------|---------|------|
| Q1 | `WorkflowResult.intermediate_data` 的 JSON Schema 是否需固化？ | A. 用 Pydantic 模型 / B. 自由 dict + 文档化 | B（handler 自定义灵活度高） |
| Q2 | Custom skill 创建时是否需要 dry-run 验证？ | A. `/api/skills/validate` 必走 / B. 可选 | A（强制预检，避免写入后才发现配置错） |
| Q3 | Skill 匹配失败的 `SKILL_EXECUTION_FAILED` 是否要附"建议重说"提示？ | A. 错误信息含示例 / B. 仅返回原始错误 | B（保持错误码简洁） |
| Q4 | `iterator: true` 的并发执行？ | A. 串行 / B. `asyncio.gather` 并发 | A（简单可预测；性能数据无瓶颈时不上并发） |
| Q5 | Skill 是否需要"启用/停用"开关？ | A. 加 `enabled: bool` 字段 / B. 删除 `skill.yaml` 即停用 | B（保持 spec 简洁；YAGNI） |
