---
title: "[Bug] notifications/initialized 返回空 body 导致 JSONDecodeError"
status: closed
labels: ["bug", "mcp"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

MCP Client 发送 `notifications/initialized` 后收到 `Invalid JSON` 错误。

**复现步骤：**
1. 启动 MCP Service 在端口 9001
2. MCP Client 执行 initialize 握手后发送 `notifications/initialized`
3. 观察客户端日志

**实际结果：**
```
Invalid JSON response from http://localhost:9001/mcp: Expecting value: line 1 column 1 (char 0)
```

**期望结果：**
握手成功，无错误。

## 根因分析

MCP 规范规定 `notifications/initialized` 应返回 HTTP 202 with **no body**。

但 `_send_initialized_notification()` 使用通用的 `_request()` 方法，该方法期望 JSON 响应：

```python
def _send_initialized_notification(self) -> None:
    self._request("POST", "/mcp", payload)  # 期望 JSON 响应

def _request(self, ...):
    response.raise_for_status()
    return response.json()  # 空 body → JSONDecodeError ❌
```

## 解决方案

`notifications/initialized` 单独处理，不期望 JSON 响应，正确处理 202 状态码。

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `app/clients/mcp_client.py` | `_send_initialized_notification()` 直接发送请求，不调用 `_request()` |

## 验证

- [x] MCP Client 初始化握手成功完成
- [x] 日志显示 "initialized notification sent"