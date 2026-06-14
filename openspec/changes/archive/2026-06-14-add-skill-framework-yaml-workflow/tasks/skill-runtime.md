# Tasks: skill-runtime

> 对应 spec: [skill-runtime](../specs/skill-runtime/spec.md)
> 覆盖原 tasks.md 组 2 / 3 / 4

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/skills/base.py` | 新建 | ~50 | `WorkflowStep` / `WorkflowResult` dataclass + `SkillHandler` 基类 |
| `app/skills/loader.py` | 新建 | ~130 | `SkillConfig` + `SkillLoader`（扫描 `skills/` + `skills_custom/`） |
| `app/skills/registry.py` | 新建 | ~110 | `SkillRegistry` + 单例 + 热加载 |
| `app/skills/__init__.py` | 新建 | ~10 | 导出 `get_skill_registry` / `init_skill_registry` |

---

## 1. `app/skills/base.py` — 数据结构与基类

### 1.1 WorkflowStep dataclass
- [ ] 1.1.1 在 `app/skills/base.py` 顶部 `import` `dataclass` / `field` / `Optional` / `List` / `Dict`（来自 `typing`）
- [ ] 1.1.2 定义 `@dataclass class WorkflowStep:` 包含字段：`id: str`、`tool: str`、`status: str = "pending"`（枚举值 `pending`/`completed`/`failed`/`pending_approval`）、`args: Optional[Dict] = None`、`result: Optional[Dict] = None`、`error: Optional[str] = None`

### 1.2 WorkflowResult dataclass
- [ ] 1.2.1 定义 `@dataclass class WorkflowResult:` 包含字段：`success: bool`、`error: Optional[str] = None`、`need_more_info: bool = False`、`need_approval: bool = False`、`intermediate_data: Optional[Dict] = None`、`steps: List[WorkflowStep] = field(default_factory=list)`
- [ ] 1.2.2 关键约束：`need_approval=True` 时 `intermediate_data` 必须含 `tool` / `tool_args` / `approval_summary` 三个 key（桥接契约）

### 1.3 SkillHandler 基类
- [ ] 1.3.1 定义 `class SkillHandler:` 包含类属性 `skill_name: str = ""`
- [ ] 1.3.2 定义 `def execute(self, message: str, context: dict) -> WorkflowResult: raise NotImplementedError`
- [ ] 1.3.3 定义 `def verify(self, result: WorkflowResult) -> bool: return result.success`（默认实现）

### 1.4 单元测试
- [ ] 1.4.1 验证 `WorkflowStep` 默认 `status="pending"`
- [ ] 1.4.2 验证 `WorkflowResult(steps=...)` 使用 `default_factory` 不共享列表

---

## 2. `app/skills/loader.py` — 加载器

### 2.1 模块级常量
- [ ] 2.1.1 计算 `_PROJECT_ROOT = Path(__file__).resolve().parents[2]`（应指向 `erp-mvp-agent/`）
- [ ] 2.1.2 计算 `_SKILLS_DIR = _PROJECT_ROOT / "skills"`
- [ ] 2.1.3 计算 `_SKILLS_CUSTOM_DIR = _PROJECT_ROOT / "skills_custom"`（决策 5）

### 2.2 SkillConfig 类
- [ ] 2.2.1 定义 `class SkillConfig:` 包含属性：`name` / `config_path: Path` / `version = "1.0"` / `description = ""` / `category = "preset"` / `intent_patterns = {"zh": [], "en": []}` / `tools: List[str] = []` / `prompt_fragment = ""` / `workflow = None` / `handler: Optional[SkillHandler] = None`
- [ ] 2.2.2 `__init__` 接收 `(name, config_path)` 赋值，**不**读盘
- [ ] 2.2.3 实现 `def load(self) -> bool:` 调用 `yaml.safe_load` 读 `self.config_path / "skill.yaml"`，填充属性；失败返回 False
- [ ] 2.2.4 实现 `def _load_handler(self, handler_path: str) -> None:` 使用 `importlib.import_module`；`sys.path.insert(0, str(self.config_path))`；解析 `"module.Class"` 形式
- [ ] 2.2.5 实现 `def get_workflow_steps(self) -> List[Dict]:` 返回 `self.workflow.get("steps", [])` 当 workflow 非空
- [ ] 2.2.6 实现 `def has_handler(self) -> bool: return self.handler is not None`
- [ ] 2.2.7 实现 `def has_yaml_workflow(self) -> bool: return self.workflow is not None and not self.has_handler()`

### 2.3 SkillLoader 类
- [ ] 2.3.1 定义 `class SkillLoader:` 包含 `__init__(skills_dir=None)` 默认使用 `_SKILLS_DIR`
- [ ] 2.3.2 实现 `def load_all(self) -> Dict[str, SkillConfig]:` 扫描两个根目录
  - 扫描 `_SKILLS_DIR` 直接子目录
  - 扫描 `_SKILLS_CUSTOM_DIR` 直接子目录（如不存在则跳过 + warn）
  - 每个子目录读取 `skill.yaml` 注册到 `self._configs`
- [ ] 2.3.3 实现 `def get_configs(self) -> Dict[str, SkillConfig]: return self._configs`
- [ ] 2.3.4 实现 `def reload(self) -> Dict[str, SkillConfig]:` 清空后重新 `load_all`
- [ ] 2.3.5 关键点：跳过以 `_` 开头的目录（如 `_template`）

### 2.4 单元测试
- [ ] 2.4.1 准备 fixture：临时目录创建 `skills/test-skill/skill.yaml`，验证能加载
- [ ] 2.4.2 验证缺失 skill.yaml 路径时 `load()` 返回 False
- [ ] 2.4.3 验证 handler 路径无效时不抛异常（仅 logger.error）
- [ ] 2.4.4 验证 `has_handler()` / `has_yaml_workflow()` 互斥

---

## 3. `app/skills/registry.py` — 注册表

### 3.1 SkillRegistry 类
- [ ] 3.1.1 定义 `class SkillRegistry:` 包含 `_configs: Dict[str, SkillConfig] = {}` / `_compiled_patterns: Dict[str, List[re.Pattern]] = {}`
- [ ] 3.1.2 实现 `def load_from_loader(self, loader: SkillLoader) -> None:` 拷贝 `_configs = loader.get_configs()`，调 `_compile_all_patterns()`
- [ ] 3.1.3 实现 `def _compile_all_patterns(self) -> None:` 遍历每个 skill 的 `intent_patterns.zh`（默认编译）/ `intent_patterns.en`（加 `re.IGNORECASE`）；`re.error` 时 `logger.warning` 跳过该 pattern
- [ ] 3.1.4 实现 `def match_skill(self, message: str) -> Optional[SkillConfig]:` 遍历 `_compiled_patterns`，命中 `pattern.search(message)` 立即返回对应 `SkillConfig`（第一个命中胜出）
- [ ] 3.1.5 实现 `def get_skill(self, name: str) -> Optional[SkillConfig]: return self._configs.get(name)`
- [ ] 3.1.6 实现 `def get_all_skills(self) -> Dict[str, SkillConfig]: return self._configs`
- [ ] 3.1.7 实现 `def add_skill(self, config: SkillConfig) -> None:` 注册到 `_configs`，重新调 `_compile_all_patterns()`（热加载）
- [ ] 3.1.8 实现 `def get_prompt_fragments(self, skill_names: List[str]) -> str:` 用 `"\n\n"` 拼接命中 skill 的 `prompt_fragment`，缺失跳过

### 3.2 全局单例
- [ ] 3.2.1 定义模块级 `_registry: Optional[SkillRegistry] = None`
- [ ] 3.2.2 实现 `def init_skill_registry() -> SkillRegistry:` 全局单例初始化（创建 `SkillLoader` → `load_all` → `SkillRegistry.load_from_loader`）
- [ ] 3.2.3 实现 `def get_skill_registry() -> Optional[SkillRegistry]: return _registry`

### 3.3 单元测试
- [ ] 3.3.1 验证中文 pattern 编译时**不**加 `re.IGNORECASE`
- [ ] 3.3.2 验证英文 pattern 编译时**加** `re.IGNORECASE`
- [ ] 3.3.3 验证 `match_skill()` 第一个匹配胜出
- [ ] 3.3.4 验证 `add_skill()` 后立即可匹配

---

## 4. `app/skills/__init__.py` — 公共 API 导出

- [ ] 4.1 添加 `from app.skills.base import SkillHandler, WorkflowStep, WorkflowResult`
- [ ] 4.2 添加 `from app.skills.loader import SkillConfig, SkillLoader`
- [ ] 4.3 添加 `from app.skills.registry import SkillRegistry, init_skill_registry, get_skill_registry`
- [ ] 4.4 添加 `__all__ = [...]` 显式导出列表
