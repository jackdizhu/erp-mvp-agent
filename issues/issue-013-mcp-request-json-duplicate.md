---
title: "[Bug] MCP Service Request.json() 被多次调用导致 500"
status: closed
labels: ["bug", "mcp"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

MCP Service 返回 500 Internal Server Error，客户端收到空响应导致 `Invalid JSON` 错误。

**复现步骤：**
1. 启动 MCP Service 在端口 9001
2. 发送 JSON-RPC 请求到 `/mcp` 端点
3. 观察服务端日志

**实际结果：**
```
Invalid JSON response from http://localhost:9001/mcp: Expecting value: line 1 column 1 (char 0)
POST / HTTP/1.1" 500 Internal Server Error
```

**期望结果：**
返回正常的 JSON-RPC 响应。

## 根因分析

`mcp_unified_endpoint()` 中 `await request.json()` 被调用了两次：

```python
async def mcp_unified_endpoint(request: Request):
    # 第一次：通过 _handle_mcp_request() 内部调用
    result = await _handle_mcp_request(request)
    
    # 第二次：再次读取 body
    try:
        body = await request.json()  # 返回空！
        method = body.get("method")
    except:
        pass
```

FastAPI/Starlette 的 Request 对象只能被解析一次。第二次调用返回空内容。

## 解决方案

移除重复的 `request.json()` 调用，只解析一次 body。

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `erp_mcp_service/main.py` | 移除重复的 `await request.json()` 调用 |

## 验证

- [x] 启动 MCP Service
- [x] 发送 `initialize` 请求，验证返回正常 JSON 响应
- [x] 发送 `tools/list` 请求，验证返回正常 JSON 响应