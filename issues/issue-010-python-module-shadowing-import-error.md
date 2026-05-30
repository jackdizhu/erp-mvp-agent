---
title: "[修复] Python包遮蔽导致 HISTORY_WINDOW 导入失败"
status: closed
labels: ["bug", "import-error"]
created: "2026-05-30"
closed: "2026-05-30"
assignee: ~
---

## 问题描述

流式连接失败，应用启动时抛出 ImportError。

**错误信息：**
```
ImportError: cannot import name 'HISTORY_WINDOW' from 'app.config'
```

**完整 Traceback：**
```
File "<app>/main.py", line 10, in <module>
    from app.agent import chat, confirm_action, stream_chat, format_sse_event
File "<app>/agent.py", line 9, in <module>
    from app.config import HISTORY_WINDOW
ImportError: cannot import name 'HISTORY_WINDOW' from 'app.config'
```

## 根因分析

**Python 包遮蔽 (Module Shadowing)**

存在两个冲突的资源：
- `app/config.py` - 包含 `HISTORY_WINDOW`、`APPROVAL_CONFIG` 等配置（原有）
- `app/config/` - Python 包目录，包含 `prompts.yaml` 和 `__init__.py`（新增）

当执行 `from app.config import HISTORY_WINDOW` 时，Python 优先找到 `app/config/` 目录包而非 `app/config.py` 文件，导致导入失败。

## 解决方案

**方案：重命名目录** `app/config/` → `app/config_dir/`

### 修改文件

| 文件 | 修改内容 |
|-----|---------|
| `app/config/` → `app/config_dir/` | 目录重命名，避免遮蔽 `app/config.py` |
| `app/prompt_config.py` | 更新导入：`from app.config_dir import load_prompts, DEFAULT_PROMPTS` |

## 验证

```bash
✓ app.config.py import OK ( HISTORY_WINDOW: {'default_n': 6} )
✓ app.config_dir import OK
✓ app.agent imports successful
✓ SYSTEM_PROMPT length: 246 chars
```

## 相关上下文

本次修复与 OpenSpec 变更 `externalize-system-prompt` 相关，该变更将 SYSTEM_PROMPT 从硬编码改为从 YAML 配置文件加载。