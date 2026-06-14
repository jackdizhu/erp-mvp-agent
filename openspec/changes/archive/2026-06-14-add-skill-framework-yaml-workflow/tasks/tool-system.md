# Tasks: tool-system (modified)

> 对应 spec: [tool-system](../specs/tool-system/spec.md)（delta — ADDED）
> 覆盖：Skill 工作流工具执行复用 `client_factory` / 工具名校验

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/executor.py` | 修改 | +5 | YAML step 调 `client_factory.execute_tool` + 风险路由 |
| `app/skills/validator.py` | 修改 | +5 | `available_tools` 去 `mcp_` 前缀校验 |
| `app/main.py` | 修改 | +3 | `/api/skills/validate` 提取 `available_tools` |

---

## 1. Skill YAML 工作流调用工具

### 1.1 executor.py:tool_call 步骤
- [ ] 1.1.1 `client_factory.execute_tool(step["tool"], resolved_params)` 直接调用
- [ ] 1.1.2 关键点：复用 `client_factory` 的 `_mcp_tool_alias` 解析（`query_order` → `mcp_query_order`）
- [ ] 1.1.3 不需要新增 tool 调用路径

### 1.2 风险等级路由
- [ ] 1.2.1 当前实现：YAML step 一律执行（即使 DANGER）
- [ ] 1.2.2 改进：DANGER 工具的 step 应返回 `pending_approval` WorkflowStep
- [ ] 1.2.3 实现：`risk = client_factory.get_risk_level(step["tool"])`，DANGER → 返回 `WorkflowResult(success=True, need_approval=True, intermediate_data={tool, tool_args, approval_summary})`
- [ ] 1.2.4 关键点：与 LLM 驱动的 DANGER 工具走同一审批流

### 1.3 单元测试
- [ ] 1.3.1 Mock `client_factory.execute_tool` 返回 success → 验证 step status="completed"
- [ ] 1.3.2 Mock `client_factory.execute_tool` 抛异常 → 验证返回 `success=False` + 错误信息
- [ ] 1.3.3 Mock `client_factory.get_risk_level` 返回 "DANGER" → 验证返回 `need_approval=True`

---

## 2. 工具可用性校验

### 2.1 validator.py:_validate_step
- [ ] 2.1.1 `available_tools` 入参已**预先**去 `mcp_` 前缀（调用方负责）
- [ ] 2.1.2 调用方：`/api/skills/validate` 端点负责提取
- [ ] 2.1.3 关键点：避免在 validator 内部耦合 MCP 注册逻辑

### 2.2 `app/main.py`:`/api/skills/validate`
- [ ] 2.2.1 `from app.clients.client_factory import client_factory`
- [ ] 2.2.2 `available_tools = [t["function"]["name"] for t in client_factory.get_all_tools()]`
- [ ] 2.2.3 关键点：`client_factory.get_all_tools()` 返回的 name 字段**已**是短名（注册时去前缀）
- [ ] 2.2.4 grep 验证：`app/main.py` 无 `mcp_` 字面前缀处理代码（统一在 `client_factory` 内部处理）

### 2.3 单元测试
- [ ] 2.3.1 注册工具 `mcp_query_order` → `available_tools` 包含 `query_order`
- [ ] 2.3.2 skill.yaml 声明 `tools: [query_order]` → 校验通过
- [ ] 2.3.3 skill.yaml 声明 `tools: [nonexistent]` → 校验失败 + 错误信息含可选工具列表

---

## 3. 工具名一致性

### 3.1 `client_factory._mcp_tool_alias` 维护
- [ ] 3.1.1 当前实现：[app/clients/client_factory.py:25-27](file:///c:/global-user-data/ai-workspace/erp-mvp-agent/app/clients/client_factory.py#L25-L27) 注册时建立 `mcp_xxx` → `xxx` 映射
- [ ] 3.1.2 不需要修改

### 3.2 跨模块一致性
- [ ] 3.2.1 `executor.py` 调 `client_factory.execute_tool("query_order", ...)` 内部自动解析为 `mcp_query_order`
- [ ] 3.2.2 `validator.py` 接收 `available_tools` 时**不**应包含 `mcp_` 前缀（避免双重剥离）
- [ ] 3.2.3 端到端验证：skill.yaml 用短名 `query_order`，运行时实际调用 `mcp_query_order`

---

## 4. 不影响范围

- [ ] 4.1 现有 9 个 ERP 工具行为不变
- [ ] 4.2 `TOOL_RISK_LEVELS` / `TOOL_LIMITS` 配置不变
- [ ] 4.3 `erp_client.execute_tool` 路径不变
- [ ] 4.4 LLM 驱动的 tool 调用流程不变（不强制走 Skill executor）
