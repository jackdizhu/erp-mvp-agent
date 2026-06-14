# Tasks: skill-api

> 对应 spec: [skill-api](../specs/skill-api/spec.md)
> 覆盖原 tasks.md 组 15（API 端点）+ 组 16（custom 示例关联）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/main.py` | 修改 | +~150 | startup hook + 5 个新端点 + 3 个 Pydantic 模型 |
| `app/main.py` import | 修改 | +3 | `import re` / `import yaml` / `from pathlib import Path` |

---

## 1. Pydantic 模型（`app/main.py` 或 `app/models.py`）

### 1.1 SkillLoadRequest
- [ ] 1.1.1 定义 `class SkillLoadRequest(BaseModel): skill_name: str`

### 1.2 SkillValidateRequest
- [ ] 1.2.1 定义 `class SkillValidateRequest(BaseModel): skill_name: str; skill_data: dict`

### 1.3 SkillCreateRequest
- [ ] 1.3.1 定义 `class SkillCreateRequest(BaseModel):` 字段：`name: str` / `description: str` / `intent_patterns: dict` / `prompt_fragment: str = ""` / `tools: list = []` / `workflow: Optional[dict] = None`
- [ ] 1.3.2 关键点：`workflow` 为可选嵌套 dict，结构由 `validator.validate_config` 校验

---

## 2. 启动钩子（`app/main.py:on_startup`）

### 2.1 注册 SkillRegistry
- [ ] 2.1.1 在 `on_startup` 内 `init_registry()` 之后调 `init_skill_registry()`（仅一次）
- [ ] 2.1.2 在 startup 日志添加 `"loaded N skills"` 计数
- [ ] 2.1.3 `init_skill_registry` 失败**不**阻断启动（仅 logger.error），但需明确文档化行为

---

## 3. 端点实现

### 3.1 GET /api/skills/available
- [ ] 3.1.1 实现 `@app.get("/api/skills/available") async def skills_available():`
- [ ] 3.1.2 registry 为 None → 返回 `[]`
- [ ] 3.1.3 遍历 `registry.get_all_skills()`，每个返回 `{name, description, category, tools, has_workflow, has_handler}`

### 3.2 GET /api/skills/loaded
- [ ] 3.2.1 实现 `@app.get("/api/skills/loaded") async def skills_loaded():`
- [ ] 3.2.2 当前 Phase 1/2 实现：返回所有已加载 skill（与 available 等价）；未来可基于 session 过滤

### 3.3 POST /api/skills/load
- [ ] 3.3.1 实现 `@app.post("/api/skills/load") async def skill_load(req: SkillLoadRequest):`
- [ ] 3.3.2 registry 为 None → `raise HTTPException(500, "Skill registry not initialized")`
- [ ] 3.3.3 `skill = registry.get_skill(req.skill_name)`，None → `raise HTTPException(404, f"Skill '{req.skill_name}' not found")`
- [ ] 3.3.4 返回 `{success: True, name, tools, has_workflow, has_handler}`

### 3.4 POST /api/skills/validate
- [ ] 3.4.1 实现 `@app.post("/api/skills/validate") async def skill_validate(req: SkillValidateRequest):`
- [ ] 3.4.2 `from app.skills.validator import SkillValidator`
- [ ] 3.4.3 `from app.clients.client_factory import client_factory`
- [ ] 3.4.4 `available_tools = [t["function"]["name"] for t in client_factory.get_all_tools()]`（已为 OpenAI 格式，**已**去前缀）
- [ ] 3.4.5 `validator = SkillValidator()` → `is_valid, errors = validator.validate_config(req.skill_data, available_tools, is_custom=True)`
- [ ] 3.4.6 返回 `{valid: is_valid, errors: errors}`

### 3.5 POST /api/skills/create
- [ ] 3.5.1 实现 `@app.post("/api/skills/create") async def skill_create(req: SkillCreateRequest):`
- [ ] 3.5.2 名称校验：`re.match(r'^[a-zA-Z0-9_-]+$', req.name)` 失败 → `HTTPException(400, "Skill 名称只允许字母、数字、下划线和连字符")`
- [ ] 3.5.3 冲突检测：`registry.get_skill(req.name)` 存在 → `HTTPException(400, f"Skill '{req.name}' 已存在")`
- [ ] 3.5.4 构造 `config_data = {name, version: "1.0", description, category: "custom", intent_patterns, tools, prompt_fragment, workflow}`
- [ ] 3.5.5 调 `validator.validate_config` 失败 → `HTTPException(400, "; ".join(errors))`
- [ ] 3.5.6 `import yaml` → 计算 `skill_dir = _PROJECT_ROOT / "skills_custom" / req.name`（决策 4 扁平）
- [ ] 3.5.7 `skill_dir.mkdir(parents=True, exist_ok=True)`
- [ ] 3.5.8 `yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)` 写 `skill.yaml`
- [ ] 3.5.9 热加载：`config = SkillConfig(name=req.name, config_path=skill_dir); config.load(); registry.add_skill(config)`
- [ ] 3.5.10 返回 `{success: True, name: req.name}`

### 3.6 单元测试 / 端到端测试
- [ ] 3.6.1 `GET /api/skills/available` 返回 N 条
- [ ] 3.6.2 `POST /api/skills/load` 不存在的 skill 返回 404
- [ ] 3.6.3 `POST /api/skills/validate` 合法配置返回 `{valid: true}`
- [ ] 3.6.4 `POST /api/skills/validate` 含 "调用 http 接口" 返回 `{valid: false, errors: [...]}`
- [ ] 3.6.5 `POST /api/skills/create` 合法返回 200，磁盘创建文件
- [ ] 3.6.6 `POST /api/skills/create` 重名返回 400
- [ ] 3.6.7 `POST /api/skills/create` 名称含空格返回 400
