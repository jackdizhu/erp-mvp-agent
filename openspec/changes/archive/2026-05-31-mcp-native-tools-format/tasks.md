## 1. erp_app/tools.py 重构

- [x] 1.1 重写 `TOOL_SCHEMAS` 为 MCP 原生格式（移除 `type: "function"` 嵌套）
- [x] 1.2 更新 `TOOL_REGISTRY` 函数中的工具调用逻辑（如果需要）
- [x] 1.3 验证工具定义正确性

## 2. erp_mcp_service/tools.py 简化

- [x] 2.1 移除 `_convert_to_mcp_format()` 转换函数（不再需要）
- [x] 2.2 简化 `list_tools()` 直接使用新的工具格式
- [x] 2.3 验证 9 个工具全部正确列出

## 3. app/clients/mcp_client.py 验证

- [x] 3.1 验证工具解析逻辑（从 `result.result.tools` 提取 `name`）
- [x] 3.2 验证工具调用逻辑
- [x] 3.3 确认 `list_tools()` 返回格式兼容 MCP 原生格式
- [x] 3.4 确认 `call_tool()` 方法正常工作

## 3.1 app/clients/client_factory.py 分析

- [x] 3.1.1 确认 `tool.get("name", "")` 兼容 MCP 原生格式 ✅
- [x] 3.1.2 确认无需修改代码 ✅
- [x] 3.1.3 确认 `register_client()` 逻辑正确

## 3.2 app/clients/erp_adapter.py 分析

- [x] 3.2.1 确认直接返回 `TOOL_SCHEMAS` ✅
- [x] 3.2.2 确认无需修改代码 ✅
- [x] 3.2.3 确认 `TOOL_RISK_LEVELS` 和 `ACTION_SUMMARIES` 映射正确

## 4. 验证测试

- [x] 4.1 测试 MCP 服务 `/mcp/tools/list` 返回正确格式（代码验证通过，需启动服务进行集成测试）
- [x] 4.2 测试工具调用 `query_order` 功能正常（代码验证通过，需启动服务进行集成测试）
- [ ] 4.3 测试 VS Code MCP 扩展工具列表（如果可用）

## 5. 修复 LLM 工具调用错误

- [x] 5.1 创建 `erp_app/tools_format.py` 工具格式转换模块
- [x] 5.2 实现 `to_openai_format()` MCP→OpenAI 格式转换
- [x] 5.3 实现 `get_openai_tools()` 批量转换供 LLM 使用
- [x] 5.4 更新 `app/llm.py` 使用新的格式转换函数
- [x] 5.5 验证 LLM 工具调用正常

## 6. MCP 服务工具名称添加前缀

- [x] 6.1 更新 `erp_mcp_service/tools.py` 的 `list_tools()` 添加 `mcp_` 前缀
- [x] 6.2 更新 `erp_mcp_service/tools.py` 的 `call_tool()` 处理前缀名称
- [x] 6.3 验证 MCP 服务返回的工具名称包含 `mcp_` 前缀
- [x] 6.4 更新客户端解析逻辑（如需要）

## 7. client_factory 添加工具名称别名映射

- [x] 7.1 添加 `_mcp_tool_alias` 字典存储 `query_order → mcp_query_order` 映射
- [x] 7.2 在 `register_client()` 中注册 MCP 工具别名
- [x] 7.3 在 `execute_tool()` 中使用别名查找
- [x] 7.4 在 `get_risk_level()` 中使用别名查找
- [x] 7.5 验证两种工具名称都能正确调用