## Context

前端 `httpUtils.js` 硬编码了 API 地址为 `http://localhost:8000`，而后端通过 `BACKEND_PORT` 环境变量配置运行在 9000 端口。这种硬编码方式导致：
- 前后端端口不一致时连接失败
- 切换环境（开发/测试/生产）需要修改源码

## Goals / Non-Goals

**Goals:**
- 前端 API 端口通过环境变量配置，默认值与后端 `BACKEND_PORT` 一致（9000）
- 保持 Vite 项目的 `.env` 约定（`VITE_` 前缀）
- 不改变现有 API 调用逻辑

**Non-Goals:**
- 不引入动态运行时配置
- 不修改后端端口配置

## Decisions

### 1. 使用 Vite 环境变量机制
**Decision**: 使用 `import.meta.env.VITE_API_PORT` 读取端口，Vite 在构建时自动注入 `.env.development` 中的值。

**Rationale**: Vite 原生支持 `.env` 文件，`VITE_` 前缀的变量会暴露给客户端代码。这是 Vite 项目的标准做法。

### 2. 默认值设为 9000
**Decision**: 代码中使用 `|| "9000"` 作为默认值，与 `.local.env` 的 `BACKEND_PORT` 一致。

**Rationale**: 确保即使没有 `.env.development` 文件，前端也能正确连接到默认后端。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 修改 `.env` 后需重启 dev server | Vite 文档明确说明 `.env` 变更需要重启 |
| 环境变量名称不统一 | 使用 `VITE_` 前缀符合 Vite 约定 |
