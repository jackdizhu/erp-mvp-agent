---
title: "[Bug] JsonRpcRequest.id 类型验证失败导致 500"
status: closed
labels: ["bug", "mcp"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

MCP Service 返回 500 Internal Server Error，ValidationError: id 字段类型验证失败。

**复现步骤：**
1. 启动 MCP Service 在端口 9001
2. 发送 JSON-RPC 请求（客户端使用整数 id，如 `id: 0`）
3. 观察服务端日志

**实际结果：**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for JsonRpcRequest
id
  Input should be a valid string [type=string_type, input_value=0, input_type=int]
POST / HTTP/1.1" 500 Internal Server Error
```

**期望结果：**
正常处理整数 id 的 JSON-RPC 请求。

## 根因分析

`JsonRpcRequest` 的 `id` 字段定义为 `Optional[str]`，但 JSON-RPC 2.0 规范中 `id` 可以是字符串、数字（int/float）或 `null`。

```python
class JsonRpcRequest(BaseModel):
    id: Optional[str] = None  # ❌ 不支持整数
```

客户端发送的 `{"id":0,...}` 导致 Pydantic 验证失败。

## 解决方案

将 `id` 类型改为 `Optional[int | str | None]`，符合 JSON-RPC 2.0 规范。

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `erp_mcp_service/main.py` | `id: Optional[int | str | None] = None` |

## 验证

- [x] 发送 id=0 的 initialize 请求，验证返回正常
- [x] 发送 id="string_id" 的请求，验证返回正常
- [x] 发送 id=null 的请求（notifications），验证返回正常