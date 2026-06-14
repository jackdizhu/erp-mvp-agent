# 方案 C：完整 Skill 框架 — YAML 工作流 + Custom Skill

## 1. 方案概述

在方案 B 的基础上，新增 YAML 工作流执行器和校验器，支持用户通过 `skill.yaml` 中的 `workflow.steps` 定义工作流。为 custom skill 做准备，实现完整的 Skill 框架。

### 核心设计决策

**工作流定义直接放在 `skill.yaml` 中，不使用独立的 `workflow.md` 文件。**

原因：
- `workflow.md` 本质是一个格式更差、解析更难的 YAML DSL — 它有严格规则（`### N.` 标记步骤、`- 类型:` 固定字段、参数必须是 JSON），用户需要学习这套 DSL 才能写
- 既然要学规则，YAML 不比 Markdown DSL 更难学，而且 YAML 有现成的 `yaml.safe_load` 解析和编辑器校验支持
- 砍掉 `workflow_parser.py`（~120 行解析代码），减少维护成本
- 每个 Skill 只需一个 `skill.yaml` 文件，不需要额外文件

### 与方案 B 的差异

```
┌─────────────────────────────────────────────────────────────┐
│              方案 B vs 方案 C 对比                            │
├──────────────────┬──────────────────┬───────────────────────┤
│ 特性             │ 方案 B           │ 方案 C                │
├──────────────────┼──────────────────┼───────────────────────┤
│ 意图匹配         │ ✅               │ ✅                    │
│ prompt 注入      │ ✅               │ ✅                    │
│ Python handler   │ ✅               │ ✅                    │
│ YAML 工作流执行  │ ❌               │ ✅                    │
│ custom skill     │ ❌               │ ✅                    │
│ 安全校验         │ ❌               │ ✅                    │
│ 按需加载 API     │ ❌               │ ✅                    │
│ 会话绑定         │ ❌               │ ✅                    │
│ 额外文件/技能    │ 0                │ 0（工作流在 yaml 内） │
│ 额外解析器       │ 0                │ 0（用 yaml.safe_load）│
└──────────────────┴──────────────────┴───────────────────────┘
```

---

## 2. 目录结构

```
erp-mvp-agent/
├── skills/                              ← Skill 数据目录
│   ├── query-order-search/
│   │   └── skill.yaml                   ← 意图匹配 + prompt 注入（无工作流）
│   ├── query-order-edit-address/
│   │   ├── skill.yaml                   ← 意图匹配 + prompt + 工作流声明
│   │   └── handler.py                   ← Python 工作流编排（preset）
│   └── custom/                          ← 用户自定义 skill
│       └── batch-query-order/
│           └── skill.yaml               ← 元数据 + prompt + workflow.steps（YAML 结构）
│                                        ← 无 handler.py，executor 直接执行 YAML 步骤
│
├── app/
│   ├── skills/                          ← Skill 运行时模块
│   │   ├── __init__.py
│   │   ├── loader.py                    ← SkillLoader（扫描+加载+校验）
│   │   ├── registry.py                  ← SkillRegistry（注册+查询+匹配）
│   │   ├── executor.py                  ← SkillExecutor（执行工作流）
│   │   ├── validator.py                 ← 安全校验 + 工具可用性校验
│   │   └── base.py                      ← SkillHandler 基类
│   ├── agent.py                         ← 修改：集成 Skill
│   ├── llm.py                           ← 修改：修复 tools 硬编码
│   ├── prompt_config.py                 ← 修改：支持 Skill prompt 注入
│   └── main.py                          ← 修改：新增 Skill API 端点
└── ...
```

与方案 B 的目录差异：
- 无 `workflow_parser.py`（不需要 Markdown 解析器）
- 无 `workflow.md` 文件（工作流定义在 `skill.yaml` 内）
- 新增 `validator.py`（安全+工具可用性校验）
- `custom/` 下的 Skill 只有一个 `skill.yaml`

---

## 3. Skill 数据格式

### 3.1 skills/query-order-search/skill.yaml（无工作流）

```yaml
name: query-order-search
version: "1.0"
description: "查询订单信息：订单状态、收货地址、预计送达时间"
category: preset

intent_patterns:
  zh:
    - "查.*订单"
    - "订单.*查询"
    - "订单.*状态"
    - "订单.*地址"
    - "订单.*送达"
    - "看看.*订单"
    - "查一下.*订单"
  en:
    - "check.*order"
    - "query.*order"
    - "order.*status"
    - "order.*address"
    - "order.*delivery"

tools:
  - query_order

prompt_fragment: |
  查询订单时，请展示以下信息：
  - 订单状态（status）
  - 收货地址（address）
  - 预计送达时间（estimated_delivery）
  如果某个字段为空，请说明"暂无数据"。

# 无工作流，LLM 自行调用 query_order 工具
workflow: null
```

### 3.2 skills/query-order-edit-address/skill.yaml（Python handler 工作流）

```yaml
name: query-order-edit-address
version: "1.0"
description: "修改订单收货地址：先查询当前地址确认，再执行修改"
category: preset

intent_patterns:
  zh:
    - "改.*收货地址"
    - "修改.*地址"
    - "更新.*收货"
    - "换.*地址"
    - "订单.*地址.*改"
  en:
    - "change.*address"
    - "update.*address"
    - "modify.*delivery"
    - "edit.*shipping"

tools:
  - query_order
  - update_order

prompt_fragment: |
  修改收货地址流程：
  1. 先查询订单当前收货地址，展示给用户确认
  2. 用户确认后，执行修改操作
  3. 修改完成后，再次查询展示新地址

# Python handler 工作流（preset skill 专用）
workflow:
  handler: "query_order_edit_address.OrderEditAddressHandler"
  steps:
    - id: query_current
      tool: query_order
      description: "查询当前订单信息"
    - id: confirm_and_update
      tool: update_order
      description: "确认后修改地址"
      requires_approval: true
    - id: verify_result
      tool: query_order
      description: "验证修改结果"
```

### 3.3 skills/custom/batch-query-order/skill.yaml（YAML 工作流，custom skill）

```yaml
name: batch-query-order
version: "1.0"
description: "批量查询订单状态"
category: custom

intent_patterns:
  zh:
    - "批量.*查询.*订单"
    - "多个.*订单.*状态"
    - "几个.*订单"
  en:
    - "batch.*query.*order"
    - "multiple.*order.*status"

tools:
  - query_order

prompt_fragment: |
  批量查询时请逐个查询并汇总为表格

# YAML 工作流定义（custom skill 无 handler.py，executor 直接执行）
workflow:
  steps:
    - id: parse_input
      type: prompt
      instruction: "从用户消息中提取所有订单号，返回 JSON 数组"

    - id: batch_query
      type: tool_call
      tool: query_order
      params:
        order_id: "{{parse_input.items[*].order_id}}"
      iterate: true
      output: order_results

    - id: summarize
      type: prompt
      instruction: "将查询结果整理为表格，包含订单号、状态、收货地址、预计送达时间"
```

### 3.4 变量引用语法

```
{{step_id.field}}               ← 引用指定步骤的输出字段
{{step_id.items[*].field}}      ← 迭代引用（配合 iterate: true）
{{message}}                     ← 用户原始消息
```

> 使用 `step_id`（而非序号）引用，因为 YAML 步骤有明确的 `id` 字段。

---

## 4. 运行时模块设计

### 4.1 app/skills/base.py — 基类与数据结构

```python
"""Skill 基类与数据结构"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class WorkflowStep:
    """工作流步骤执行结果"""
    id: str
    tool: str
    status: str = "pending"          # pending | completed | failed | pending_approval
    args: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    success: bool
    error: Optional[str] = None
    need_more_info: bool = False     # 需要更多信息（让 LLM 继续对话）
    need_approval: bool = False      # 需要审批
    intermediate_data: Optional[Dict] = None
    steps: List[WorkflowStep] = field(default_factory=list)


class SkillHandler:
    """Skill 工作流处理器基类（preset skill 的 Python handler）"""

    skill_name: str = ""

    def execute(self, message: str, context: dict) -> WorkflowResult:
        """执行工作流，子类必须实现"""
        raise NotImplementedError

    def verify(self, result: WorkflowResult) -> bool:
        """验证工作流结果，子类可选实现"""
        return result.success
```

### 4.2 app/skills/loader.py — SkillLoader

```python
"""Skill 加载器：扫描 skills/ 目录，加载 skill.yaml"""
import yaml
import logging
import importlib
import sys
from pathlib import Path
from typing import Dict, Optional, List

from app.skills.base import SkillHandler

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _PROJECT_ROOT / "skills"


class SkillConfig:
    """单个 Skill 的配置"""

    def __init__(self, name: str, config_path: Path):
        self.name = name
        self.config_path = config_path
        self.version = "1.0"
        self.description = ""
        self.category = "preset"          # preset | custom
        self.intent_patterns = {"zh": [], "en": []}
        self.tools: List[str] = []
        self.prompt_fragment = ""
        self.workflow = None              # dict 或 None
        self.handler: Optional[SkillHandler] = None
        self._loaded = False

    def load(self) -> bool:
        """加载 skill.yaml"""
        yaml_path = self.config_path / "skill.yaml"
        if not yaml_path.exists():
            logger.warning(f"skill.yaml not found in {self.config_path}")
            return False

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            self.version = data.get("version", "1.0")
            self.description = data.get("description", "")
            self.category = data.get("category", "preset")
            self.intent_patterns = data.get("intent_patterns", {"zh": [], "en": []})
            self.tools = data.get("tools", [])
            self.prompt_fragment = data.get("prompt_fragment", "")
            self.workflow = data.get("workflow")

            # 加载 Python handler（preset skill）
            if self.workflow and self.workflow.get("handler"):
                self._load_handler(self.workflow["handler"])

            self._loaded = True
            return True

        except Exception as e:
            logger.error(f"Failed to load skill {self.name}: {e}")
            return False

    def _load_handler(self, handler_path: str):
        """动态加载 Python handler 模块"""
        parts = handler_path.rsplit(".", 1)
        if len(parts) != 2:
            logger.error(f"Invalid handler path: {handler_path}")
            return

        module_name, class_name = parts
        handler_dir = self.config_path

        try:
            if str(handler_dir) not in sys.path:
                sys.path.insert(0, str(handler_dir))
            module = importlib.import_module(module_name)
            handler_class = getattr(module, class_name)
            self.handler = handler_class()
            logger.info(f"Loaded handler {handler_path} for skill {self.name}")
        except Exception as e:
            logger.error(f"Failed to load handler {handler_path}: {e}")

    def get_workflow_steps(self) -> List[Dict]:
        """获取工作流步骤列表（从 skill.yaml 的 workflow.steps 读取）"""
        if not self.workflow:
            return []
        return self.workflow.get("steps", [])

    def has_handler(self) -> bool:
        """是否有 Python handler"""
        return self.handler is not None

    def has_yaml_workflow(self) -> bool:
        """是否有 YAML 工作流（无 handler 时由 executor 执行）"""
        return self.workflow is not None and not self.has_handler()


class SkillLoader:
    """扫描并加载所有 Skill"""

    def __init__(self, skills_dir: Optional[Path] = None):
        self._skills_dir = skills_dir or _SKILLS_DIR
        self._configs: Dict[str, SkillConfig] = {}

    def load_all(self) -> Dict[str, SkillConfig]:
        """扫描 skills/ 目录，加载所有 skill"""
        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return {}

        for item in self._skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                yaml_path = item / "skill.yaml"
                if yaml_path.exists():
                    config = SkillConfig(name=item.name, config_path=item)
                    if config.load():
                        self._configs[item.name] = config
                        logger.info(f"Loaded skill: {item.name}")

            # 扫描 custom/ 子目录
            if item.is_dir() and item.name == "custom":
                for custom_item in item.iterdir():
                    if custom_item.is_dir() and not custom_item.name.startswith("_"):
                        yaml_path = custom_item / "skill.yaml"
                        if yaml_path.exists():
                            config = SkillConfig(name=custom_item.name, config_path=custom_item)
                            if config.load():
                                self._configs[custom_item.name] = config
                                logger.info(f"Loaded custom skill: {custom_item.name}")

        return self._configs

    def get_configs(self) -> Dict[str, SkillConfig]:
        return self._configs

    def reload(self) -> Dict[str, SkillConfig]:
        self._configs.clear()
        return self.load_all()
```

### 4.3 app/skills/registry.py — SkillRegistry

```python
"""Skill 注册表：意图匹配 + 查询"""
import re
import logging
from typing import Optional, Dict, List

from app.skills.loader import SkillConfig, SkillLoader

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Skill 注册与意图匹配"""

    def __init__(self):
        self._configs: Dict[str, SkillConfig] = {}
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}

    def load_from_loader(self, loader: SkillLoader):
        """从 SkillLoader 加载所有 Skill"""
        self._configs = loader.get_configs()
        self._compile_all_patterns()
        logger.info(f"SkillRegistry loaded {len(self._configs)} skills")

    def _compile_all_patterns(self):
        """编译所有意图匹配正则"""
        self._compiled_patterns.clear()
        for name, config in self._configs.items():
            patterns = []
            for p in config.intent_patterns.get("zh", []):
                try:
                    patterns.append(re.compile(p))
                except re.error:
                    logger.warning(f"Invalid pattern in skill {name}: {p}")
            for p in config.intent_patterns.get("en", []):
                try:
                    patterns.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    logger.warning(f"Invalid pattern in skill {name}: {p}")
            self._compiled_patterns[name] = patterns

    def match_skill(self, message: str) -> Optional[SkillConfig]:
        """匹配用户消息到 Skill，返回优先级最高的匹配"""
        for name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(message):
                    logger.info(f"Skill matched: {name} for message: {message[:50]}...")
                    return self._configs[name]
        return None

    def get_skill(self, name: str) -> Optional[SkillConfig]:
        return self._configs.get(name)

    def get_all_skills(self) -> Dict[str, SkillConfig]:
        return self._configs

    def add_skill(self, config: SkillConfig):
        """动态添加 Skill（custom skill 创建后热加载）"""
        self._configs[config.name] = config
        self._compile_all_patterns()

    def get_prompt_fragments(self, skill_names: List[str]) -> str:
        """获取指定 Skill 的 prompt_fragment 拼接"""
        fragments = []
        for name in skill_names:
            config = self._configs.get(name)
            if config and config.prompt_fragment:
                fragments.append(config.prompt_fragment)
        return "\n\n".join(fragments)


# 全局单例
_registry: Optional[SkillRegistry] = None


def init_skill_registry() -> SkillRegistry:
    global _registry
    loader = SkillLoader()
    loader.load_all()
    _registry = SkillRegistry()
    _registry.load_from_loader(loader)
    return _registry


def get_skill_registry() -> Optional[SkillRegistry]:
    return _registry
```

### 4.4 app/skills/validator.py — 安全校验 + 工具可用性校验

```python
"""Skill 校验器：安全检查 + 工具可用性验证"""
import re
import logging
from typing import List, Tuple, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# 禁止出现在 custom skill 中的关键词
FORBIDDEN_PATTERNS = [
    re.compile(r'(?:file|文件)\s*(?:read|write|读写|读取|写入)', re.IGNORECASE),
    re.compile(r'(?:http|fetch|request|api|接口)\s*(?:call|request|请求|调用)', re.IGNORECASE),
    re.compile(r'(?:forward|proxy|转发|代理)', re.IGNORECASE),
    re.compile(r'(?:exec|eval|system|subprocess|os\.)', re.IGNORECASE),
    re.compile(r'(?:import|from\s+\w+\s+import)', re.IGNORECASE),
]


class SkillValidator:
    """校验 Skill 配置的安全性和可用性"""

    def validate_config(self, config_data: Dict,
                        available_tools: List[str],
                        is_custom: bool = True) -> Tuple[bool, List[str]]:
        """
        校验 skill.yaml 解析后的数据

        Args:
            config_data: yaml.safe_load 后的字典
            available_tools: 当前可用的 MCP 工具列表
            is_custom: 是否为用户自定义 skill（更严格校验）

        Returns:
            (is_valid, errors)
        """
        errors = []

        # 1. 基础字段校验
        if not config_data.get("name"):
            errors.append("Skill 名称不能为空")
        if not config_data.get("description"):
            errors.append("Skill 描述不能为空")

        # 2. 意图规则校验
        patterns = config_data.get("intent_patterns", {})
        if not patterns.get("zh") and not patterns.get("en"):
            errors.append("至少需要定义一种语言的意图匹配规则")

        # 3. 工具列表校验
        tools = config_data.get("tools", [])
        if not tools:
            errors.append("Skill 必须声明依赖的工具列表")

        # 4. 工作流校验
        workflow = config_data.get("workflow")
        if workflow:
            workflow_errors = self._validate_workflow(workflow, available_tools, is_custom)
            errors.extend(workflow_errors)

        # 5. custom skill 额外安全校验
        if is_custom:
            security_errors = self._validate_security(config_data)
            errors.extend(security_errors)

            # custom skill 不能有 handler
            if workflow and workflow.get("handler"):
                errors.append("自定义 Skill 不允许使用 Python handler，只能使用 YAML 工作流")

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Skill validation failed: {errors}")
        return is_valid, errors

    def _validate_workflow(self, workflow: Dict, available_tools: List[str],
                           is_custom: bool) -> List[str]:
        """校验工作流定义"""
        errors = []

        # 有 handler 的工作流，步骤声明仅供参考，不需要严格校验
        if workflow.get("handler"):
            return errors

        # YAML 工作流步骤校验
        steps = workflow.get("steps", [])
        if not steps:
            errors.append("工作流至少需要一个步骤")
            return errors

        for i, step in enumerate(steps):
            step_errors = self._validate_step(step, i, available_tools)
            errors.extend(step_errors)

        return errors

    def _validate_step(self, step: Dict, index: int,
                       available_tools: List[str]) -> List[str]:
        """校验单个步骤"""
        errors = []
        step_id = step.get("id", f"step_{index}")

        step_type = step.get("type")
        if not step_type:
            errors.append(f"步骤 '{step_id}' 缺少 type 字段")
            return errors

        if step_type == "tool_call":
            tool = step.get("tool")
            if not tool:
                errors.append(f"步骤 '{step_id}' 缺少 tool 字段")
            elif tool not in available_tools:
                errors.append(
                    f"步骤 '{step_id}' 引用了未注册的工具 '{tool}'，"
                    f"可用工具: {', '.join(available_tools)}"
                )

            if not step.get("params"):
                errors.append(f"步骤 '{step_id}' 缺少 params 字段")

        elif step_type == "prompt":
            if not step.get("instruction"):
                errors.append(f"步骤 '{step_id}' 缺少 instruction 字段")

        else:
            errors.append(f"步骤 '{step_id}' 类型无效: {step_type}，仅支持 tool_call 和 prompt")

        return errors

    def _validate_security(self, config_data: Dict) -> List[str]:
        """custom skill 安全校验"""
        errors = []

        # 收集所有文本内容
        full_text = config_data.get("description", "")
        full_text += " " + config_data.get("prompt_fragment", "")

        workflow = config_data.get("workflow", {})
        for step in workflow.get("steps", []):
            if step.get("instruction"):
                full_text += " " + step["instruction"]

        for pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(full_text)
            if match:
                errors.append(
                    f"安全校验失败：包含禁止的操作 '{match.group()}'，"
                    f"自定义 Skill 不支持文件读写、接口调用、转发等高风险操作"
                )

        return errors

    def validate_skill_dir(self, skill_dir: Path, is_custom: bool = True) -> Tuple[bool, List[str]]:
        """校验 skill 目录的完整性"""
        errors = []

        yaml_path = skill_dir / "skill.yaml"
        if not yaml_path.exists():
            errors.append("缺少 skill.yaml 配置文件")
            return False, errors

        if is_custom:
            # custom skill 不能有 handler.py
            handler_path = skill_dir / "handler.py"
            if handler_path.exists():
                errors.append("自定义 Skill 不允许包含 handler.py 代码文件")

        is_valid = len(errors) == 0
        return is_valid, errors
```

### 4.5 app/skills/executor.py — SkillExecutor（支持 Python handler 和 YAML 工作流）

```python
"""Skill 工作流执行器 — 支持 Python handler 和 YAML 工作流"""
import re
import logging
from typing import Optional, Dict, Any, List

from app.skills.base import SkillHandler, WorkflowResult, WorkflowStep
from app.skills.loader import SkillConfig

logger = logging.getLogger(__name__)


class SkillExecutor:
    """执行 Skill 工作流（Python handler 或 YAML 工作流）"""

    def execute(self, skill: SkillConfig, message: str,
                context: dict, available_tools: List[str]) -> Optional[WorkflowResult]:
        """
        执行 Skill 工作流

        优先级：
        1. Python handler（preset skill）
        2. YAML 工作流（custom skill 或 preset skill 无 handler 时）
        3. 无工作流（仅 prompt 注入）
        """
        # 优先使用 Python handler
        if skill.has_handler():
            return self._execute_handler(skill, message, context)

        # 尝试使用 YAML 工作流
        if skill.has_yaml_workflow():
            steps = skill.get_workflow_steps()
            if steps:
                return self._execute_yaml_workflow(steps, message, context, available_tools)

        # 无工作流
        logger.info(f"Skill {skill.name} has no workflow, prompt injection only")
        return None

    def _execute_handler(self, skill: SkillConfig, message: str,
                         context: dict) -> Optional[WorkflowResult]:
        """执行 Python handler"""
        try:
            result = skill.handler.execute(message, context)
            logger.info(f"Skill {skill.name} handler executed: success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Skill {skill.name} handler failed: {e}")
            return WorkflowResult(success=False, error=str(e))

    def _execute_yaml_workflow(self, steps: List[Dict], message: str,
                               context: dict, available_tools: List[str]) -> WorkflowResult:
        """执行 skill.yaml 中定义的 YAML 工作流"""
        from app.clients.client_factory import client_factory

        steps_result = []
        step_outputs = {"message": message}

        for step_def in steps:
            step_id = step_def.get("id", "unknown")
            step_type = step_def.get("type")

            if step_type == "tool_call":
                # 解析参数中的变量引用
                raw_params = step_def.get("params", {})
                resolved_params = self._resolve_params(raw_params, step_outputs)

                if step_def.get("iterate", False):
                    result = self._execute_iterative(
                        step_id, step_def.get("tool"), resolved_params, client_factory
                    )
                else:
                    try:
                        result = client_factory.execute_tool(
                            step_def["tool"], resolved_params
                        )
                    except Exception as e:
                        steps_result.append(WorkflowStep(
                            id=step_id, tool=step_def.get("tool", ""),
                            status="failed", error=str(e)
                        ))
                        return WorkflowResult(
                            success=False,
                            error=f"步骤 '{step_id}' 执行失败: {e}",
                            steps=steps_result
                        )

                steps_result.append(WorkflowStep(
                    id=step_id, tool=step_def.get("tool", ""),
                    result=result, status="completed"
                ))

                output_var = step_def.get("output")
                if output_var:
                    step_outputs[output_var] = result

            elif step_type == "prompt":
                # prompt 步骤：记录指令，由 LLM 处理
                steps_result.append(WorkflowStep(
                    id=step_id, tool="prompt",
                    status="completed",
                    result={"instruction": step_def.get("instruction", "")}
                ))

        return WorkflowResult(
            success=True,
            steps=steps_result,
            intermediate_data=step_outputs
        )

    def _resolve_params(self, params: Dict, step_outputs: Dict) -> Dict:
        """解析参数中的变量引用 {{step_id.field}}"""
        if not params:
            return params

        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self._replace_variables(value, step_outputs)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, step_outputs)
            else:
                resolved[key] = value
        return resolved

    def _replace_variables(self, template: str, step_outputs: Dict) -> str:
        """替换模板变量 {{step_id.field}} 或 {{message}}"""
        def replacer(match):
            var_path = match.group(1)
            if var_path == "message":
                return step_outputs.get("message", "")

            # step_id.field 或 step_id.items[*].field
            parts = var_path.split(".", 1)
            if len(parts) == 2:
                step_id, path = parts
                step_data = step_outputs.get(step_id, {})
                return self._get_nested(step_data, path)

            return match.group(0)

        return re.sub(r'\{\{(.+?)\}\}', replacer, template)

    def _get_nested(self, data: Any, path: str) -> str:
        """获取嵌套字段值"""
        parts = path.replace("[*]", "").split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, "")
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else ""
            else:
                return str(current)
        return str(current)

    def _execute_iterative(self, step_id: str, tool: str,
                           params: Dict, client_factory) -> List:
        """迭代执行工具调用"""
        results = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    item_params = {k: v for k, v in params.items() if k != key}
                    item_params[key.rstrip("s")] = item
                    try:
                        result = client_factory.execute_tool(tool, item_params)
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e)})
                return results

        # 非数组参数，单次调用
        result = client_factory.execute_tool(tool, params)
        return [result]
```

---

## 5. API 端点

### 5.1 新增端点

```python
# app/main.py 新增

@app.get("/api/skills/available")
async def skills_available():
    """列出所有可加载的 Skill"""
    registry = get_skill_registry()
    if not registry:
        return []
    skills = []
    for name, config in registry.get_all_skills().items():
        skills.append({
            "name": name,
            "description": config.description,
            "category": config.category,
            "tools": config.tools,
            "has_workflow": config.workflow is not None,
            "has_handler": config.has_handler(),
        })
    return skills


@app.get("/api/skills/loaded")
async def skills_loaded():
    """列出当前已加载的 Skill"""
    registry = get_skill_registry()
    if not registry:
        return []
    return [
        {"name": name, "description": config.description, "category": config.category}
        for name, config in registry.get_all_skills().items()
    ]


class SkillLoadRequest(BaseModel):
    skill_name: str


@app.post("/api/skills/load")
async def skill_load(req: SkillLoadRequest):
    """按需加载 Skill（预留接口）"""
    registry = get_skill_registry()
    if not registry:
        raise HTTPException(status_code=500, detail="Skill registry not initialized")
    skill = registry.get_skill(req.skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{req.skill_name}' not found")
    return {
        "success": True,
        "name": skill.name,
        "tools": skill.tools,
        "has_workflow": skill.workflow is not None,
        "has_handler": skill.has_handler(),
    }


class SkillValidateRequest(BaseModel):
    skill_name: str
    skill_data: dict                    # skill.yaml 的完整内容


@app.post("/api/skills/validate")
async def skill_validate(req: SkillValidateRequest):
    """校验 custom skill 配置"""
    from app.skills.validator import SkillValidator

    validator = SkillValidator()
    available_tools = [t["function"]["name"] for t in client_factory.get_all_tools()]
    is_valid, errors = validator.validate_config(req.skill_data, available_tools, is_custom=True)

    return {"valid": is_valid, "errors": errors}


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    intent_patterns: dict
    prompt_fragment: str = ""
    tools: list = []
    workflow: dict = None               # workflow.steps 等


@app.post("/api/skills/create")
async def skill_create(req: SkillCreateRequest):
    """创建自定义 Skill"""
    import yaml
    from app.skills.validator import SkillValidator
    from app.skills.loader import SkillConfig

    # 1. 校验名称合法性
    if not re.match(r'^[a-zA-Z0-9_-]+$', req.name):
        raise HTTPException(status_code=400, detail="Skill 名称只允许字母、数字、下划线和连字符")

    # 2. 校验名称不重复
    registry = get_skill_registry()
    if registry and registry.get_skill(req.name):
        raise HTTPException(status_code=400, detail=f"Skill '{req.name}' 已存在")

    # 3. 构建配置数据并校验
    config_data = {
        "name": req.name,
        "version": "1.0",
        "description": req.description,
        "category": "custom",
        "intent_patterns": req.intent_patterns,
        "tools": req.tools,
        "prompt_fragment": req.prompt_fragment,
        "workflow": req.workflow,
    }

    validator = SkillValidator()
    available_tools = [t["function"]["name"] for t in client_factory.get_all_tools()]
    is_valid, errors = validator.validate_config(config_data, available_tools, is_custom=True)

    if not is_valid:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # 4. 写入文件
    skill_dir = _PROJECT_ROOT / "skills" / "custom" / req.name
    skill_dir.mkdir(parents=True, exist_ok=True)

    with open(skill_dir / "skill.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

    # 5. 热加载到 registry
    if registry:
        config = SkillConfig(name=req.name, config_path=skill_dir)
        if config.load():
            registry.add_skill(config)

    return {"success": True, "name": req.name}
```

---

## 6. custom skill 创建流程

```
┌─────────────────────────────────────────────────────────────┐
│              用户创建 Custom Skill 流程                       │
└─────────────────────────────────────────────────────────────┘

  1. 用户在前端填写 Skill 信息
     ├── 名称、描述
     ├── 意图匹配规则
     ├── 依赖的工具列表（从当前可用工具中选择）
     ├── prompt_fragment
     └── 工作流步骤（可视化编辑器，输出为 YAML 结构）

  2. 前端调用 POST /api/skills/validate
     ├── 传入 skill_data（YAML 结构的 JSON）
     └── 后端校验格式 + 安全性 + 工具可用性

  3. 校验通过后，前端调用 POST /api/skills/create
     ├── 后端写入 skills/custom/{name}/skill.yaml
     └── 热加载到 SkillRegistry

  4. 后续对话中命中意图时自动调用
```

---

## 7. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/skills/__init__.py` | 新增 | 导出 |
| `app/skills/base.py` | 新增 | SkillHandler 基类 + 数据结构 |
| `app/skills/loader.py` | 新增 | SkillLoader（扫描+加载+handler 加载） |
| `app/skills/registry.py` | 新增 | SkillRegistry（意图匹配+动态添加） |
| `app/skills/executor.py` | 新增 | SkillExecutor（Python handler + YAML 工作流执行） |
| `app/skills/validator.py` | 新增 | 安全校验 + 工具可用性校验 |
| `skills/query-order-search/skill.yaml` | 新增 | 查询订单 Skill |
| `skills/query-order-edit-address/skill.yaml` | 新增 | 修改地址 Skill |
| `skills/query-order-edit-address/handler.py` | 新增 | 修改地址 Python handler |
| `app/agent.py` | 修改 | 集成 Skill 意图匹配 |
| `app/llm.py` | 修改 | 修复 tools 硬编码 |
| `app/prompt_config.py` | 修改 | 支持 skill_fragments |
| `app/main.py` | 修改 | startup + Skill API 端点 |

---

## 8. 风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| YAML 工作流变量引用解析复杂 | 中 | 仅支持简单引用和迭代，边界情况明确处理 |
| custom skill 创建 API 需前端配合 | 中 | 先实现后端 API，前端后续迭代 |
| 工作流执行中审批流程集成 | 高 | YAML 工作流的 tool_call 步骤若为 DANGER 级别，需中断等待审批 |
| handler.py 动态 import 安全 | 中 | 仅加载 skills/ 目录下 preset handler，custom 禁止 |
| 迭代执行的性能 | 低 | 当前订单量级小，逐条调用可接受 |
| custom skill 热加载后意图冲突 | 低 | 后注册的 Skill 覆盖同名 pattern，新增时检查重名 |

---

## 9. 与方案 B 的迁移路径

方案 C 是方案 B 的超集，可以从 B 平滑升级：

```
Phase 1: 实现方案 B
  ├── app/skills/ 基础模块（loader, registry, executor, base）
  ├── 2 个 preset skill
  └── agent.py / llm.py / prompt_config.py 修改

Phase 2: 扩展到方案 C
  ├── 新增 validator.py
  ├── executor.py 扩展 YAML 工作流执行
  ├── 新增 Skill API 端点（validate, create, available, loaded, load）
  └── 新增 custom skill 创建流程
```

Phase 1 的代码在 Phase 2 中完全复用，无需重写。

### 方案 C 相比原 workflow.md 版本的简化

| 项目 | 原 workflow.md 版本 | 当前 YAML 版本 |
|------|---------------------|----------------|
| 额外解析器 | workflow_parser.py (~120 行) | 无（用 yaml.safe_load） |
| 额外文件/技能 | workflow.md | 无（工作流在 skill.yaml 内） |
| 解析容错 | 差（Markdown 格式敏感） | 好（YAML 规范） |
| 变量引用 | {{stepN.var}}（序号） | {{step_id.var}}（ID 引用，更稳定） |
| 校验方式 | 先解析 Markdown 再校验 | 直接校验 YAML 字段 |
