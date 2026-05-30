## Why

当前所有代码耦合在单一 `app/` 包中，agent 核心逻辑（LLM 调用、意图检测、审批状态管理）与 ERP 业务逻辑（工具实现、Mock 数据、库存规则）混杂在一起。随着工具数量增长和对接真实数据库的需求，这种架构无法支持独立扩展、测试和维护。

具体痛点：
- `mock_erp.py` 使用内存字典，数据无法持久化，重启即丢失
- `tools.py` 单文件包含全部 9 个工具实现，不符合单一职责
- `approval.py` 直接引用 `mock_erp` 的 `orders`/`inventory` 字典，agent 与 ERP 数据层紧耦合
- `config.py` 混合了 agent 配置和 ERP 工具配置

## What Changes

- **拆分代码为两个逻辑服务包**：`app/` (Agent Core) 和 `erp_app/` (ERP Service)，同进程内通过函数调用通信
- **引入 SQLite 数据层**：替代 `mock_erp.py` 的内存字典，实现数据持久化，支持未来平滑迁移到真实数据库
- **工具自描述**：`TOOL_SCHEMAS` 和 `TOOL_REGISTRY` 迁移到 `erp_app/`，agent 通过 `erp_client.py` 薄适配层获取 schemas 和执行工具
- **审批流拆分**：审批状态管理（pending_actions dict、TTL、确认）留在 `app/approval_core.py`；审批详情生成（查询原数据对比）改为通过 erp 接口获取
- **业务逻辑分层**：`erp_app/` 按服务拆分为 `order_service.py`、`inventory_service.py`、`supplier_service.py`
- **新增 HTTP API**：ERP 服务暴露 `/erp/orders/`、`/erp/inventory/`、`/erp/suppliers/` 路由，agent 内部调用（未来可独立为 HTTP 服务）

## Capabilities

### New Capabilities
- `erp-service`: ERP 服务包，包含 SQLite 数据层、业务逻辑层和工具注册中心
- `sqlite-persistence`: 使用 SQLite 替代内存字典存储订单、库存、供应商数据
- `erp-client`: Agent 调用 ERP 的薄适配层接口，实现服务间解耦
- `erp-internal-api`: ERP 内部 HTTP 路由，为未来独立服务部署预留

### Modified Capabilities
- `tool-system`: 工具注册从 `app/tools.py` 迁移到 `erp_app/tools.py`，agent 通过 client 调用而非直接引用
- `mock-erp`: 从内存字典升级为 SQLite 持久化存储，数据模型和 CRUD 逻辑迁移到 `erp_app/`
- `approval-flow`: 审批详情生成改为通过 erp 查询接口获取原数据，不再直接引用内存字典
- `agent-core`: 工具 schemas 来源从本地 `TOOL_SCHEMAS` 改为通过 `erp_client.get_tools()` 获取

## Impact

- **目录结构**: 新增 `erp_app/` 包（约 12 个新文件），`app/` 包精简（删除 `tools.py`、`mock_erp.py`，拆分 `approval.py`）
- **数据迁移**: 原有内存字典数据需迁移为 SQLite seed 脚本，启动时自动初始化
- **API 路由**: 主 FastAPI app 新增 mount `erp_app.main` 的路由，`/erp/*` 端点供 agent 内部调用
- **配置拆分**: `config.py` 拆分为 `app/config.py`（agent 配置）和 `erp_app/config.py`（ERP 配置）
- **错误分类**: `errors.py` 拆分为 agent 错误和 ERP 错误两类
- **兼容性**: 现有 `/chat`、`/chat/confirm`、`/chat/stream` 端点保持不变，前端无感知
