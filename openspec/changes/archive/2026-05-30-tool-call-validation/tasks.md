# Tasks: tool-call-validation

## 1. 意图检测引擎

- [x] 1.1 创建 `app/config/intent_rules.json` 配置文件，包含4个DANGER工具的中英文关键词模式
- [x] 1.2 创建 `app/intent_detector.py` 文件，实现 `detect_tool_intent(message: str) -> Optional[str]` 函数
- [x] 1.3 实现从JSON文件加载配置的逻辑，支持 `INTENT_RULES_PATH` 环境变量覆盖默认路径
- [x] 1.4 实现配置验证逻辑，无效配置时回退到内置默认规则
- [x] 1.5 实现 `reload_intent_rules()` 函数，支持运行时重新加载配置
- [x] 1.6 编写单元测试覆盖：中文意图检测、英文意图检测、无意图场景、配置加载、配置回退

## 2. 工具调用验证（节点1）

- [x] 2.1 修改 `app/agent.py` 的 `chat()` 函数，在无 tool_calls 时调用 `detect_tool_intent()`
- [x] 2.2 实现 `_force_tool_retry(messages, message, expected_tool, previous_reply)` 函数，构造二次LLM调用
- [x] 2.3 在 `app/errors.py` 中新增 `llm_retry_exhausted()` 错误构造函数
- [x] 2.4 处理二次调用仍失败的场景，返回 LLM_RETRY_EXHAUSTED 错误
- [x] 2.5 编写单元测试覆盖：幻觉拦截、二次调用成功、二次调用失败、无意图放行

## 3. 审批流程验证（节点2）

- [x] 3.1 修改 `app/agent.py` 的 `_handle_tool_calls()` 函数，跟踪是否有 DANGER 工具被执行
- [x] 3.2 在 DANGER 工具处理分支中，检测 `create_pending()` 返回值，None 时返回 APPROVAL_FAILED 错误
- [x] 3.3 在函数末尾增加验证：`if has_danger_tools_executed and not pending_action` → 返回 APPROVAL_REQUIRED 错误
- [x] 3.4 在 `app/errors.py` 中新增 `approval_failed()` 和 `approval_required()` 错误构造函数
- [x] 3.5 编写单元测试覆盖：审批创建成功、审批创建失败(max_pending)、逻辑错误漏创建、SAFE工具跳过验证

## 4. 集成测试

- [x] 4.1 测试场景：输入"修改订单123地址" → LLM 幻觉 → 拦截 → 二次调用 → 返回审批卡片
- [x] 4.2 测试场景：输入"取消订单124" → LLM 正确调用 → 审批验证通过 → 返回审批卡片
- [x] 4.3 测试场景：输入"订单123状态" → LLM 正确调用 query_order → 不触发二次调用
- [x] 4.4 测试场景：中英文混合输入意图检测
- [x] 4.5 性能测试：正常场景延迟无影响，幻觉场景额外延迟 < 3秒

## 5. 文档更新

- [x] 5.1 更新 `docs/erp-mvp-agent.md`，添加工具调用验证和意图检测章节
- [x] 5.2 更新 `README.md` 和 `README.zh.md`，说明安全校验机制
