## Why

前端 `httpUtils.js` 硬编码 `API_BASE = "http://localhost:8000"`，而后端 `.local.env` 配置 `BACKEND_PORT=9000`，导致前端请求端口不匹配，所有 API 调用（包括流式聊天）均因网络不通失败。需要从环境变量读取端口，保持前后端配置一致。

## What Changes

- 前端新增 `.default.env` 文件，定义 `VITE_API_PORT=9000`
- 前端新增 `.development.env` 文件，定义 `VITE_API_PORT=9000`
- 前端 `httpUtils.js` 将硬编码端口改为从 `import.meta.env.VITE_API_PORT` 读取，默认值 9000
- 更新 `.gitignore` 确保 `.env.*` 不被提交（如已有则跳过）

## Capabilities

### New Capabilities
- `frontend-api-config`: 前端 API 基础地址的环境变量配置能力

### Modified Capabilities
<!-- 无 -->

## Impact

- 前端文件：`frontend/src/httpUtils.js`、`frontend/.default.env`、`frontend/.development.env`
- 不影响后端
- 修复后需重启前端开发服务器以加载新环境变量
