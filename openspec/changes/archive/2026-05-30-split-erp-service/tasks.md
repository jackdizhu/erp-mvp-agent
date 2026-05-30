## 1. ERP 服务包基础设施

- [x] 1.1 创建 `erp_app/__init__.py` 空模块
- [x] 1.2 创建 `erp_app/config.py`，迁移 TOOL_RISK_LEVELS、TOOL_LIMITS、ACTION_SUMMARIES（从 app/config.py）
- [x] 1.3 创建 `erp_app/errors.py`，迁移 DATA_* 和 SYS_* 错误类型（从 app/errors.py，保留不迁移的 agent 错误在 app/errors.py）
- [x] 1.4 创建 `erp_app/main.py`，定义 APIRouter 并挂载到 `/erp` 前缀

## 2. SQLite 数据层

- [x] 2.1 创建 `erp_app/db.py`，实现 SQLite 连接管理、数据库初始化、表创建（orders、order_items、inventory、suppliers、supplier_items）
- [x] 2.2 创建 `erp_app/models.py`，定义 Order、OrderItem、Inventory、Supplier、SupplierItem 的 Pydantic/dataclass 模型
- [x] 2.3 创建 `erp_app/seed.py`，实现演示数据初始化（3 个订单、2 个库存、2 个供应商及其关联项）
- [x] 2.4 在 `db.py` 实现 CRUD  helpers：query_order、query_orders_batch、create_order、update_order、cancel_order、delete_order、query_inventory、update_inventory、query_supplier、query_supplier_with_items

## 3. 业务服务层

- [x] 3.1 创建 `erp_app/services/__init__.py` 空模块
- [x] 3.2 创建 `erp_app/services/order_service.py`，迁移订单相关逻辑（状态机转换、字段修改规则、库存预留/释放）
- [x] 3.3 创建 `erp_app/services/inventory_service.py`，迁移库存逻辑（recalc_available、库存调整）
- [x] 3.4 创建 `erp_app/services/supplier_service.py`，迁移供应商查询逻辑

## 4. 工具注册与执行

- [x] 4.1 创建 `erp_app/tools.py`，定义 TOOL_SCHEMAS（9 个工具 schema）、TOOL_REGISTRY（映射到 service 层函数）、execute_tool 执行器
- [x] 4.2 创建 `erp_app/approval_detail.py`，实现审批详情生成函数（查询 SQLite 获取原数据，对比 old vs new，返回 fields + irreversible）
- [x] 4.3 在 `erp_app/main.py` 添加 `/erp/tools/schemas`、`/erp/tools/execute`、`/erp/approval/detail` 路由

## 5. Agent 侧适配层

- [x] 5.1 创建 `app/erp_client.py`，实现 ErpClient 类：get_tools()、execute_tool()、get_approval_detail()，内部调用 erp_app 函数
- [x] 5.2 创建 `app/approval_core.py`，从 `app/approval.py` 拆分出审批状态管理（pending_actions dict、TTL、cleanup、summary 模板填充）
- [x] 5.3 重构 `app/agent.py`：TOOL_SCHEMAS 来源改为 `erp_client.get_tools()`，execute_tool 改为 `erp_client.execute_tool()`，审批详情改为 `erp_client.get_approval_detail()`
- [x] 5.4 拆分 `app/approval.py`：保留调用 approval_core + erp_client 生成完整 pending action 的逻辑，或直接移除由 agent.py 直接调用两个组件

## 6. 配置与入口精简

- [x] 6.1 精简 `app/config.py`，移除已迁移到 erp_app 的配置项（TOOL_RISK_LEVELS、TOOL_LIMITS、ACTION_SUMMARIES、APPROVAL_CONFIG），保留 HISTORY_WINDOW、SSE_CONFIG
- [x] 6.2 精简 `app/main.py`，保留 /chat、/chat/confirm、/chat/stream 路由，mount erp_app.router 到 `/erp`
- [x] 6.3 更新 `app/main.py` 的 imports，移除对 tools.py、mock_erp.py 的引用
- [x] 6.4 在 `app/main.py` 添加启动时 erp_app 数据库初始化调用

## 7. 清理与验证

- [x] 7.1 删除 `app/mock_erp.py`（已由 SQLite + seed.py 替代）
- [x] 7.2 删除 `app/tools.py`（已迁移到 erp_app）
- [x] 7.3 更新 `app/requirements.txt`，确保 sqlite3 可用（Python 内置，无需额外安装）
- [x] 7.4 启动后端服务，验证所有 8 个 MVP 场景正常工作
- [x] 7.5 验证前端聊天功能不受影响（查询、创建、审批全流程）