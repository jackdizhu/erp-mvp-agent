---
title: "[Bug] MCP Service URL 路径重复拼接导致 404"
status: closed
labels: ["bug", "mcp"]
created: "2026-05-31"
closed: "2026-05-31"
assignee: ~
---

## 问题描述

MCP Client 请求时报 404，URL 显示为 `http://localhost:9001/mcp/mcp`（路径重复）。

**复现步骤：**
1. 启动 MCP Service 在端口 9001
2. 配置 `mcp_servers.json` 的 `url` 为 `http://localhost:9001/mcp`（含 `/mcp` 路径）
3. Agent 启动时初始化 MCP Client

**实际结果：**
```
http://localhost:9001/mcp/mcp  (路径重复)
404 Client Error: Not Found for url: http://localhost:9001/mcp/mcp
```

**期望结果：**
```
http://localhost:9001/mcp  (单一正确路径)
```

## 根因分析

`mcp_client.py` 的 `_request()` 方法：
```python
def _request(self, method: str, path: str, json_data: Optional[dict] = None) -> dict:
    url = f"{self.endpoint}{path}"  # endpoint + /mcp = /mcp/mcp
```

`mcp_servers.json` 配置了 `url: "http://localhost:9001/mcp"`（包含路径），而代码又在 path 参数中传入 `/mcp`，导致重复拼接。

## 解决方案

统一规范：endpoint 只包含 host:port，路径在代码中固定追加。

- JSON 配置：`"url": "http://localhost:9001"`（不含 `/mcp`）
- 环境变量：`MCP_SERVICE_URL=http://localhost:9001`（不含 `/mcp`）
- 代码固定追加 `/mcp` 路径

## 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `app/config_dir/mcp_servers.json` | url 从 `http://localhost:9001/mcp` 改为 `http://localhost:9001` |
| `.env` | MCP_SERVICE_URL=http://localhost:9001 |
| `app/clients/mcp_registry.py` | 日志输出 URL 来源（env/config） |

## 验证

- [x] 启动 MCP Service，验证 `curl http://localhost:9001/mcp` 返回正常
- [x] Agent 启动日志显示 `MCP service URL from env/config: http://localhost:9001/mcp`