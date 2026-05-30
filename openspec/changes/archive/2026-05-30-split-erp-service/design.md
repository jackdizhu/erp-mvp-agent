## Context

当前系统为单一 `app/` 包，包含 8 个 Python 文件。Agent 核心（LLM 调用、意图检测、审批状态、风险路由）与 ERP 业务（工具实现、Mock 数据、库存规则、状态机）直接耦合。`approval.py` 直接引用 `mock_erp.orders`/`inventory` 字典，`tools.py` 单文件包含 9 个工具实现，`mock_erp.py` 使用内存字典无持久化。

系统已有一个活跃的 OpenSpec 变更 `add-tool-plugin-system`（工具插件化+审批 Pipeline 升级），本变更与其正交：本变更聚焦**包级拆分和数据层升级**，`add-tool-plugin-system` 聚焦**工具动态加载和审批 Pipeline 增强**。两者可在不同阶段合并。

## Goals / Non-Goals

**Goals:**
- 将代码拆分为 `app/`（Agent Core）和 `erp_app/`（ERP Service）两个独立包
- 用 SQLite 替代 `mock_erp.py` 的内存字典，实现数据持久化
- 工具注册（`TOOL_SCHEMAS` + `TOOL_REGISTRY`）迁移到 `erp_app/`，实现 ERP 自描述
- 审批流拆分为状态管理（agent）和详情生成（erp）
- 保持现有 `/chat` API 完全兼容，前端零感知
- 接口设计按 HTTP 风格，方便未来独立为 HTTP 服务

**Non-Goals:**
- 不做真正的进程拆分（保持单进程函数调用）
- 不做工具插件动态加载（属于 `add-tool-plugin-system` 的范围）
- 不做审批 Pipeline 升级（属于 `add-tool-plugin-system` 的范围）
- 不做审计日志、批量审批（属于 `add-tool-plugin-system` 的范围）
- 不修改前端代码

## Decisions

### D1: 进程内函数调用 vs HTTP 通信

**决策**: 使用进程内直接函数调用，不使用 HTTP。

**理由**: 
- MVP 阶段部署简单性优先
- 零网络延迟，无超时/重试复杂度
- 通过 `erp_client.py` 薄适配层封装，内部接口按 request/response 对象设计，未来可无缝替换为 HTTP 调用

**替代方案**: HTTP 通信 — 过早引入网络复杂度，MVP 阶段无收益。

### D2: SQLite vs 其他数据库

**决策**: 使用 SQLite，文件存储在项目根目录 `data/erp.db`。

**理由**:
- 零配置，无需额外数据库服务
- 单文件便携，适合 MVP 和开发测试
- 标准 SQL，未来迁移到 PostgreSQL 成本低
- Python 内置 `sqlite3` 模块，无额外依赖

### D3: 审批流拆分边界

**决策**: 
- `app/approval_core.py`: 管理 pending_actions 内存字典、TTL、清理、summary 模板填充
- `erp_app/approval_detail.py`: 接收 tool_name + args，查询 SQLite 获取原数据（如订单当前状态），对比 old vs new，返回 fields + irreversible

**理由**: 审批状态是 agent 交互行为（何时需要审批、超时多久），审批详情需要 ERP 数据（原值是什么），拆分后 agent 不再直接引用 ERP 数据字典。

### D4: 工具注册归属

**决策**: `TOOL_SCHEMAS` 和 `TOOL_REGISTRY` 完全放在 `erp_app/tools.py`。Agent 通过 `erp_client.get_tools()` 获取 schemas 传给 LLM，通过 `erp_client.execute_tool()` 执行。

**理由**: ERP 自描述能力，未来新增/修改工具只需改动 erp_app，agent 代码无需感知。

### D5: 数据库初始化策略

**决策**: 使用 `seed.py` 在首次启动时初始化演示数据（与原 `mock_erp.py` 的 3 个订单、2 个库存、2 个供应商一致），通过 `IF NOT EXISTS` 检查避免重复初始化。

**理由**: 保持与现有演示数据一致，前端行为不变。

### D6: 配置拆分

**决策**: 
- `app/config.py`: 保留 `HISTORY_WINDOW`, `SSE_CONFIG`
- `erp_app/config.py`: 迁移 `TOOL_RISK_LEVELS`, `TOOL_LIMITS`, `APPROVAL_CONFIG`, `ACTION_SUMMARIES`
- `APPROVAL_CONFIG` 拆分为两部分：TTL/max_pending 留在 agent（审批状态配置），summary 模板留在 erp（审批详情配置）

### D7: 数据模型设计

**决策**: 
- `orders` + `order_items` 分离为两张表（原内存字典中 items 是嵌套数组）
- `suppliers` + `supplier_items` 分离为两张表（原 items 是 SKU 数组）
- 库存直接存 `qty` + `reserved`，`available` 通过查询时计算或 trigger 维护

### D8: ERP 内部 API 路由

**决策**: `erp_app/main.py` 定义 `APIRouter`，mount 到主 app 的 `/erp` 前缀下。路由仅供 agent 内部调用，不对外暴露给前端。

```
/erp/tools/schemas     GET  → 返回 TOOL_SCHEMAS
/erp/tools/execute     POST → 执行工具调用
/erp/approval/detail   POST → 获取审批详情
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 进程内调用无真正的服务隔离 | 未来拆分需改造通信层 | `erp_client.py` 按 HTTP 风格设计接口，改造成本低 |
| SQLite 并发写入锁 | 多用户同时操作可能锁库 | MVP 阶段单用户可接受；Phase 2 迁移 PostgreSQL 解决 |
| `approval_detail` 增加一次数据库查询 | 审批详情生成延迟增加 | 查询为单行 SELECT，影响可忽略 |
| 与 `add-tool-plugin-system` 变更交叉 | 合并时可能冲突 | 本变更聚焦包拆分和 SQLite，不触碰插件化和 Pipeline，冲突面小 |
| `tools.py` 迁移后 agent 依赖方向反转 | 原 `agent → tools` 变为 `agent → erp_client → erp_app/tools` | 依赖方向更清晰，agent 不再知道工具实现细节 |

## Migration Plan

```
Step 1: 创建 erp_app/ 目录结构
Step 2: 实现 db.py (SQLite 连接 + CRUD)
Step 3: 实现 models.py (数据模型)
Step 4: 实现 seed.py (初始化演示数据)
Step 5: 实现 services/ (order, inventory, supplier)
Step 6: 迁移 tools.py 到 erp_app/
Step 7: 实现 erp_app/config.py + errors.py
Step 8: 实现 erp_app/approval_detail.py
Step 9: 实现 erp_app/main.py (router)
Step 10: 实现 app/erp_client.py (薄适配层)
Step 11: 拆分 app/approval.py → approval_core.py
Step 12: 重构 app/agent.py 使用 erp_client
Step 13: 精简 app/main.py + app/config.py
Step 14: 删除 mock_erp.py
Step 15: 全量测试验证
```

**Rollback**: 保留 `mock_erp.py` 作为备份分支，回滚时恢复 `tools.py` 和 `approval.py` 原始版本即可。

## Open Questions

1. **数据库路径配置**: `data/erp.db` 路径是否应通过环境变量配置？
2. **SQLite WAL 模式**: 是否启用 WAL (Write-Ahead Logging) 提升并发性能？
3. **erp_client 是否应缓存 tool schemas**: 每次 LLM 调用都获取 schemas 还是缓存一次？
