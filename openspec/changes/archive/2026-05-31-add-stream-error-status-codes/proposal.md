## Why

流式连接失败时，前端仅显示通用错误消息"流式连接失败，请重试"，无法提供具体的错误状态码和详细信息，导致问题难以定位和分析。需要增强前后端错误处理链路，传递详细的 HTTP 状态码、错误原因和上下文信息。

## What Changes

- 前端 httpUtils.js：捕获流式请求失败时的 HTTP 状态码和错误详情，传递给上层回调
- 前端 useStreamingChat.js：增强错误对象，包含 status、statusText、message 等字段
- 前端 ChatPage.jsx：onError 回调显示详细错误信息（状态码 + 原因），替换通用提示
- 后端 main.py：流式接口添加错误日志记录，包含请求上下文和异常堆栈
- 后端 mcp_client.py：HTTP 请求失败时记录详细状态码、URL 和响应内容

## Capabilities

### New Capabilities
- `stream-error-diagnostics`: 流式请求错误的详细诊断信息传递和展示能力

### Modified Capabilities
<!-- 无现有能力需要修改 -->

## Impact

- 前端文件：httpUtils.js、useStreamingChat.js、ChatPage.jsx
- 后端文件：main.py、mcp_client.py
- 不影响现有功能，仅增强错误信息传递和日志记录
- 前端错误提示更加具体，辅助用户和开发者快速定位问题
