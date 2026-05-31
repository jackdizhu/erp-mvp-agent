---
title: "MCP Service 架构集成导入错误"
status: closed
labels: ["bug", "mcp-service"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: ~
---

## 问题描述

MCP Service 架构集成后，多个文件存在导入路径错误导致服务无法启动。

**复现步骤：**
1. 执行 `start.sh` 启动所有服务
2. Backend 启动失败，报 ImportError

**实际结果：**
```
ImportError: cannot import name 'TOOL_RISK_LEVELS' from 'erp_app.tools'
```

**期望结果：**
Backend 正常启动，服务间通信正常。

## 根因分析

| 文件 | 问题 | 根因 |
|------|------|------|
| `erp_mcp_service/tools.py` | `sys.path.insert` 在 `import sys` 之前 | 代码顺序错误 |
| `erp_mcp_service/config.py` | 使用 `Path` 未导入 | 缺少 import 语句 |
| `app/clients/erp_adapter.py` | 从 `erp_app.tools` 导入 `TOOL_RISK_LEVELS`/`ACTION_SUMMARIES` | 错误的模块来源，这些常量定义在 `erp_app.config` |

## 解决方案

### 1. erp_mcp_service/tools.py
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### 2. erp_mcp_service/config.py
```python
import os
from pathlib import Path
from dotenv import load_dotenv
```

### 3. app/clients/erp_adapter.py
```python
from erp_app.tools import TOOL_SCHEMAS, execute_tool
from erp_app.config import TOOL_RISK_LEVELS, ACTION_SUMMARIES
```

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `erp_mcp_service/tools.py` | 修正 sys.path 导入顺序 |
| `erp_mcp_service/config.py` | 增加 `from pathlib import Path` |
| `erp_mcp_service/main.py` | 增加 DB init 和 seed 启动事件 |
| `app/clients/erp_adapter.py` | 修正 TOOL_RISK_LEVELS/ACTION_SUMMARIES 导入路径 |

## 验证

- [x] Backend 启动成功
- [x] MCP Service 启动成功
- [x] Frontend 启动成功
- [x] 工具调用正常（MCP 和 local fallback 均工作）
- [x] 无 ImportError 报错
