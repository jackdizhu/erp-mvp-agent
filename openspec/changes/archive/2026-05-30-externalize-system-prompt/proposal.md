## Why

SYSTEM_PROMPT 硬编码在 `app/llm.py` 中，导致：
1. 修改提示词需要改代码
2. 业务数据（供应商A: SUP-A, iPhone-15）与提示词耦合
3. 能力列表与 tools.py 定义可能不同步

需要将提示词外部化为配置文件，实现提示词与代码分离。

## What Changes

- 新增 `app/config/prompts.yaml` 配置文件存储提示词模板
- 修改 `app/config.py` 添加 `load_prompts()` 加载函数
- 新增 `build_system_prompt()` 函数，从 YAML 配置和 TOOL_SCHEMAS 动态生成 SYSTEM_PROMPT
- 移除 `app/llm.py` 中的硬编码 SYSTEM_PROMPT
- 简化提示词：移除硬编码业务数据（供应商/SKU），由 erp_app 按需提供

## Capabilities

### New Capabilities

- `prompt-config`: 提示词配置管理能力
  - YAML 配置文件定义角色、风险提示、回复风格
  - 自动从 TOOL_SCHEMAS 生成能力列表
  - 支持变量替换和模板化

### Modified Capabilities

- `agent-core`: Agent 核心能力中的 SYSTEM_PROMPT 来源变更（从硬编码改为动态生成）

## Impact

- `app/llm.py`: 移除硬编码 SYSTEM_PROMPT，改为从配置加载
- `app/agent.py`: 无需修改，仅使用 `build_system_prompt()` 生成的提示词
- `app/config/`: 新增 prompts.yaml 配置文件
- `erp_app/tools.py`: 无需修改，TOOL_SCHEMAS 作为数据源被引用
