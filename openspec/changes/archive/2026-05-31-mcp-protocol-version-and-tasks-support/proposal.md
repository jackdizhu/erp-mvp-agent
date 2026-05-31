## Why

MCP Service 当前使用协议版本 2025-03-26，导致新版 IDE (如 TRAE) 无法连接，因为它们使用更新的协议版本 2025-11-25。同时，部分业务操作（如批量查询订单）耗时较长，需要 MCP Tasks 功能支持异步追踪和进度反馈。

## What Changes

1. **协议版本升级**
   - 更新 `PROTOCOL_VERSION` 为 `2025-11-25`
   - 服务端声明新版协议支持
   - 旧版客户端（mcp_client.py）同样升级版本

2. **MCP Tasks 功能支持**
   - 实现 `tasks/start`, `tasks/status`, `tasks/list`, `tasks/cancel`, `tasks/complete` 方法
   - 支持工具级别的 `taskSupport` 声明
   - 在 capabilities 中声明 `tasks` 支持
   - 创建任务状态管理器

3. **工具批量操作优化**
   - `query_orders` 工具声明 `taskSupport: "optional"`
   - 批量查询时支持异步任务追踪

## Capabilities

### New Capabilities
- `mcp-tasks`: MCP Tasks 异步任务管理，支持长时间运行操作的状态追踪
- `mcp-tool-task-support`: 工具级别的 Task 支持声明

### Modified Capabilities
- 无（现有功能保持不变）

## Impact

- **修改文件**:
  - `erp_mcp_service/main.py` - 版本常量更新、Tasks 方法实现
  - `app/clients/mcp_client.py` - 版本常量更新
  - `erp_mcp_service/tools.py` - 工具 taskSupport 声明
- **新增文件**:
  - `erp_mcp_service/task_manager.py` - 任务状态管理
- **测试影响**:
  - IDE 连接测试（验证 2025-11-25 兼容性）
  - 批量操作测试（验证 Tasks 功能）