## Context

当前 `app/llm.py` 中 SYSTEM_PROMPT 硬编码如下：

```python
SYSTEM_PROMPT = """你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。

你可以执行以下操作：
- 查询订单状态、批量查询订单
- 查询库存信息、查询供应商信息
...

系统已有以下参考数据：
- 供应商A: SUP-A, 供应商B: SUP-B
- 商品SKU: iPhone 15 = "iPhone-15", MacBook Pro 14 = "MacBook-Pro"
...

当用户使用供应商名或商品名时，请自动映射到对应编号并调用工具。"""
```

存在问题：
1. 业务数据硬编码在提示词中，不便于维护
2. 能力列表与 `erp_app/tools.py` 的 TOOL_SCHEMAS 不同步
3. 修改提示词需要改代码并重新部署

## Goals / Non-Goals

**Goals:**
- 将提示词配置外部化为 YAML 文件
- 能力列表自动从 TOOL_SCHEMAS 生成
- 移除硬编码业务数据，按需从 erp_app 获取
- 支持多环境差异化配置（如测试/生产环境）

**Non-Goals:**
- 不实现提示词的运行时编辑（通过 API 修改）
- 不实现提示词版本管理
- 不实现提示词 A/B 测试

## Decisions

### D1: 使用 YAML 配置文件

**Decision**: 在 `app/config/prompts.yaml` 定义提示词模板

**Rationale**:
- YAML 格式对运营人员友好，易于编辑
- 支持多环境配置（prompts.yaml, prompts.prod.yaml）
- 与现有 `intent_rules.json` 互补

**Alternatives Considered**:
- .env 环境变量：多行文本管理不便
- JSON 配置文件：嵌套结构不够直观
- Python 配置模块：需要开发者编辑

### D2: 提示词结构分离

**Decision**: 提示词分为静态配置 + 动态生成两部分

```yaml
# prompts.yaml
system_prompt:
  role: "你是ERP智能助手..."
  risk_notice: "对于修改、取消、删除等高风险操作..."
  response_style: "请用简洁专业的中文回复用户。"
  capabilities_header: "你可以执行以下操作："
  capabilities_footer: ""  # 可选的后缀说明
```

**Rationale**:
- 静态部分（角色、风格）可配置
- 动态部分（能力列表）自动生成，确保与 TOOL_SCHEMAS 同步

### D3: 移除硬编码业务数据

**Decision**: 删除提示词中的"系统已有以下参考数据"段落

**Rationale**:
- 供应商/商品/SKU 映射应由 LLM 从工具参数描述中学习
- 如需注入业务上下文，可通过额外的 system message 注入
- 减少 token 消耗

**Impact**:
- 原 `iPhone-15` → `iPhone 15` 映射由工具参数 description 提供
- 供应商映射同理

### D4: 动态生成能力列表

**Decision**: 能力列表从 `erp_app/tools.py` 的 TOOL_SCHEMAS 自动生成

```python
def build_capabilities_list(tools: list) -> str:
    lines = []
    for tool in tools:
        desc = tool["function"]["description"]
        lines.append(f"- {desc}")
    return "\n".join(lines)
```

**Rationale**:
- 保证与工具定义100%同步
- 无需手动维护两份列表
- 新增工具自动生效

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 提示词结构变更需改 YAML | 运营人员需要理解配置格式 | 提供示例模板和注释 |
| 动态生成的能力列表过长 | token 消耗增加 | 可通过配置限制数量 |
| YAML 文件加载失败 | Agent 无法启动 | 提供硬编码 fallback |

## Migration Plan

### Phase 1: 配置文件创建
1. 创建 `app/config/prompts.yaml`
2. 创建 `app/prompt_config.py` 加载函数
3. 实现 `build_system_prompt()` 函数

### Phase 2: 集成测试
1. 修改 `app/llm.py` 使用动态生成的 SYSTEM_PROMPT
2. 测试不同工具组合场景
3. 验证回退逻辑

### Rollback
- 删除 `prompts.yaml`
- 将原硬编码 SYSTEM_PROMPT 恢复
- 移除 prompt_config.py 中的加载逻辑

## Open Questions

1. 是否需要支持提示词模板变量（如 `{date}`, `{user_name}`）？
2. 是否需要多语言支持（中文/English）？
