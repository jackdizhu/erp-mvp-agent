## Context

当前 `erp_mcp_service` 采用 REST 风格多路由设计，将 `tools/list` 和 `tools/call` 拆分为独立 URL 路径。MCP Streamable HTTP 规范（2025-03-26）要求服务端暴露单一 HTTP 端点，客户端通过 JSON-RPC `method` 字段区分操作类型。Trae IDE 的 MCP 客户端遵循规范，POST 到根路径 `/`，导致 404 错误。

此外，端口 8001 被其他 Node.js 服务占用，MCP Service URL 硬编码在 `mcp_servers.json` 中，无法通过环境变量灵活调整。

现有架构：

```
IDE MCP Client                    erp_mcp_service (FastAPI)
     │                                    │
     ├── POST / ──────────────────────────▶│ 404 (无路由)
     ├── POST /mcp/tools/list ───────────▶│ ✅ (但 IDE 不会调这里)
     └── POST /mcp/tools/call ───────────▶│ ✅ (但 IDE 不会调这里)
```

## Goals / Non-Goals

**Goals:**

- MCP Service 符合 Streamable HTTP 规范，Trae IDE 可正常发现和连接
- 实现 `initialize` 握手，完成 MCP 协议必需的生命周期
- 端口和 URL 通过环境变量可配置，避免端口冲突
- 保留旧路由兼容，内部客户端可渐进迁移

**Non-Goals:**

- 不实现 SSE 流式响应（规范可选，当前工具调用均为同步返回）
- 不实现 `GET /mcp` 服务端推送（规范可选）
- 不实现 `DELETE /mcp` 会话终止（规范可选）
- 不实现 `Mcp-Session-Id` 会话管理（当前单客户端场景不需要）
- 不实现 JSON-RPC batch 请求处理

## Decisions

### D1: 端点路径 — 同时支持 `/mcp` 和 `/`

**选择**: 主端点 `/mcp`，同时注册 `/` 作为兼容端点

**备选方案**:
- A: 仅 `/mcp` — 规范推荐，但 IDE 默认 POST 到 `/`，需修改 IDE 配置
- B: 仅 `/` — IDE 开箱即用，但语义不明确，与其他路由冲突风险高
- C: 同时支持 `/mcp` 和 `/` — 兼容性最好

**理由**: IDE 配置 `http://localhost:9001` 时 POST 到 `/`，配置 `http://localhost:9001/mcp` 时 POST 到 `/mcp`。两种都能工作，降低用户配置门槛。

### D2: 旧路由处理 — 保留并标记 deprecated

**选择**: 保留 `/mcp/tools/list` 和 `/mcp/tools/call`，内部重用统一处理逻辑

**备选方案**:
- A: 直接删除 — 简洁但破坏内部客户端
- B: 保留并重定向 — 增加不必要的 HTTP 跳转
- C: 保留并复用逻辑 — 兼容性好，代码复用

**理由**: 内部 `mcp_client.py` 迁移需要时间，保留旧路由确保渐进迁移。旧路由内部调用统一的 method 分发函数，避免逻辑重复。

### D3: initialize 握手 — 服务端无状态实现

**选择**: 服务端不维护会话状态，`initialize` 请求直接返回能力声明

**备选方案**:
- A: 有状态会话 — 生成 session ID，存储客户端能力
- B: 无状态 — 每次请求独立处理，initialize 仅返回服务端信息

**理由**: 当前 ERP MCP Service 是单用户本地服务，不需要多会话隔离。无状态实现简单，避免会话管理复杂度。未来如需多会话支持，可增量添加 `Mcp-Session-Id`。

### D4: MCP Client 握手 — 懒初始化

**选择**: `MCPClient` 在首次 `list_tools()` 或 `call_tool()` 时自动执行握手

**备选方案**:
- A: 构造时握手 — 创建客户端时立即 initialize
- B: 懒初始化 — 首次工具调用时握手
- C: 显式初始化 — 需要调用方手动调用 `connect()`

**理由**: 懒初始化对调用方透明，不改变 `MCPClient` 的使用方式。构造时握手可能在服务未就绪时失败，懒初始化可以配合重试机制。

### D5: 环境变量覆盖 — URL 级别覆盖

**选择**: 新增 `MCP_SERVICE_URL` 环境变量，整体覆盖 `mcp_servers.json` 中的 URL

**备选方案**:
- A: 分别覆盖 host/port — 粒度细但配置繁琐
- B: 整体覆盖 URL — 一次配置，简单直接
- C: 仅覆盖端口 — 不够灵活，无法改变路径

**理由**: `MCP_SERVICE_URL=http://localhost:9001/mcp` 一次设置覆盖完整地址，包含协议、主机、端口和路径。比分别设置 host/port 更简洁。

### D6: 协议版本 — 硬编码 2025-03-26

**选择**: 服务端硬编码 `protocolVersion: "2025-03-26"`，不实现版本协商

**理由**: 当前仅支持一个协议版本，版本协商增加复杂度但无实际收益。未来支持多版本时可改为配置化。

## Risks / Trade-offs

- **[旧路由长期维护负担]** → 旧路由复用统一逻辑，维护成本极低。在下个大版本可移除
- **[无会话管理导致多客户端冲突]** → 当前为本地单用户场景，风险极低。如需多客户端，增量添加 session
- **[懒初始化首次调用延迟]** → 握手仅增加一次 HTTP 往返（~10ms），可接受
- **[环境变量覆盖 JSON 配置的优先级不直观]** → 在日志中明确输出实际使用的 URL，便于排查

## Migration Plan

1. 部署新版 MCP Service（端口 9001）
2. 更新 Trae IDE MCP 配置：`http://localhost:9001` 或 `http://localhost:9001/mcp`
3. 设置环境变量 `MCP_SERVICE_URL=http://localhost:9001/mcp`（可选，覆盖 JSON 配置）
4. 内部客户端 `mcp_client.py` 自动使用新端点，无需额外操作
5. 旧路由继续可用，无需立即迁移
6. 回滚：设置 `MCP_SERVICE_PORT=8001`，恢复旧配置
