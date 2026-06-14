# Tasks: chat-api (modified)

> 对应 spec: [chat-api](../specs/chat-api/spec.md)（delta — ADDED 5 个端点）
> 覆盖原 tasks.md 组 15（API 端点实现）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/main.py` | 修改 | +200 | 3 个 Pydantic 模型 + 5 个端点 + startup hook |
| `app/main.py` import | 修改 | +3 | `re` / `yaml` / `pathlib.Path` |

---

## 1. Pydantic 模型（`app/main.py` 中定义）

### 1.1 SkillLoadRequest
- [ ] 1.1.1 `class SkillLoadRequest(BaseModel): skill_name: str`

### 1.2 SkillValidateRequest
- [ ] 1.2.1 `class SkillValidateRequest(BaseModel): skill_name: str; skill_data: dict`

### 1.3 SkillCreateRequest
- [ ] 1.3.1 `class SkillCreateRequest(BaseModel):` 字段定义完整（参考 spec）
- [ ] 1.3.2 关键点：`workflow: Optional[dict] = None`（嵌套 dict 校验由 validator 负责）

---

## 2. startup hook 扩展（`app/main.py:on_startup`）

### 2.1 注册 SkillRegistry
- [ ] 2.1.1 在 `init_registry()` 之后调 `init_skill_registry()`
- [ ] 2.1.2 关键点：Skill 初始化在 MCP 之后（依赖 client_factory）
- [ ] 2.1.3 失败时 logger.error 但**不**阻断启动（前端可继续访问）
- [ ] 2.1.4 启动日志添加 `"Skill registry initialized with N skills"`

---

## 3. 端点 1: GET /api/skills/available

### 3.1 实现
- [ ] 3.1.1 `@app.get("/api/skills/available")`
- [ ] 3.1.2 `registry = get_skill_registry()`
- [ ] 3.1.3 registry 为 None → `return []`
- [ ] 3.1.4 遍历 `registry.get_all_skills().items()`，构造：
  ```python
  {
      "name": name,
      "description": config.description,
      "category": config.category,
      "tools": config.tools,
      "has_workflow": config.workflow is not None,
      "has_handler": config.has_handler(),
  }
  ```

### 3.2 单元测试
- [ ] 3.2.1 空 registry → `[]`
- [ ] 3.2.2 含 3 个 skill → 数组 3 项，字段完整

---

## 4. 端点 2: GET /api/skills/loaded

### 4.1 实现
- [ ] 4.1.1 `@app.get("/api/skills/loaded")`
- [ ] 4.1.2 Phase 1/2 实现：返回所有已加载 skill（与 available 等价）
- [ ] 4.1.3 未来按 session_id 过滤（保留扩展点）

---

## 5. 端点 3: POST /api/skills/load

### 5.1 实现
- [ ] 5.1.1 `@app.post("/api/skills/load")`
- [ ] 5.1.2 registry None → `raise HTTPException(500, "Skill registry not initialized")`
- [ ] 5.1.3 `skill = registry.get_skill(req.skill_name)` 不存在 → `HTTPException(404, f"Skill '{req.skill_name}' not found")`
- [ ] 5.1.4 返回 `{success: True, name, tools, has_workflow, has_handler}`

---

## 6. 端点 4: POST /api/skills/validate

### 6.1 实现
- [ ] 6.1.1 `@app.post("/api/skills/validate")`
- [ ] 6.1.2 `from app.skills.validator import SkillValidator`（端点内 import）
- [ ] 6.1.3 `from app.clients.client_factory import client_factory`
- [ ] 6.1.4 `available_tools = [t["function"]["name"] for t in client_factory.get_all_tools()]`
- [ ] 6.1.5 关键点：`client_factory.get_all_tools()` 返回 OpenAI 格式 dict，**已**去 `mcp_` 前缀（在注册时处理）
- [ ] 6.1.6 `validator = SkillValidator()` → `is_valid, errors = validator.validate_config(req.skill_data, available_tools, is_custom=True)`
- [ ] 6.1.7 返回 `{valid: is_valid, errors: errors}`

### 6.2 单元测试
- [ ] 6.2.1 合法 preset 风格 config（即使 is_custom=True）→ `{valid: true}`（无 workflow 校验宽松）
- [ ] 6.2.2 含 `from foo import bar` → `{valid: false, errors: ["安全校验失败..."]}`
- [ ] 6.2.3 tools 引用不存在的工具 → `{valid: false, errors: ["工具 'xxx' 未注册..."]}`

---

## 7. 端点 5: POST /api/skills/create

### 7.1 实现
- [ ] 7.1.1 `@app.post("/api/skills/create")`
- [ ] 7.1.2 `import re` / `import yaml` / `from pathlib import Path`（端点内或顶部 import）
- [ ] 7.1.3 名称校验：`if not re.match(r'^[a-zA-Z0-9_-]+$', req.name): raise HTTPException(400, ...)`
- [ ] 7.1.4 冲突检测：`if registry and registry.get_skill(req.name): raise HTTPException(400, ...)`
- [ ] 7.1.5 构造 `config_data = {"name": req.name, "version": "1.0", "description": req.description, "category": "custom", "intent_patterns": req.intent_patterns, "tools": req.tools, "prompt_fragment": req.prompt_fragment, "workflow": req.workflow}`
- [ ] 7.1.6 调 `validator.validate_config(config_data, available_tools, is_custom=True)`，失败 → `HTTPException(400, "; ".join(errors))`
- [ ] 7.1.7 `_PROJECT_ROOT = Path(__file__).resolve().parents[1]`
- [ ] 7.1.8 `skill_dir = _PROJECT_ROOT / "skills_custom" / req.name`（**不**是 `skills/custom/`）
- [ ] 7.1.9 `skill_dir.mkdir(parents=True, exist_ok=True)`
- [ ] 7.1.10 `with open(skill_dir / "skill.yaml", "w", encoding="utf-8") as f: yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)`
- [ ] 7.1.11 热加载：`config = SkillConfig(name=req.name, config_path=skill_dir); config.load(); registry.add_skill(config)`
- [ ] 7.1.12 返回 `{success: True, name: req.name}`

### 7.2 关键路径验证
- [ ] 7.2.1 grep 验证 `app/main.py` 中**无** `"skills" / "custom"` 路径字面量
- [ ] 7.2.2 grep 验证 `skill_dir` 路径**以** `skills_custom` 开头

### 7.3 单元测试
- [ ] 7.3.1 合法请求 → 200 + 磁盘创建文件
- [ ] 7.3.2 重名 → 400 + "已存在"
- [ ] 7.3.3 名称含空格 → 400 + "只允许字母、数字、下划线和连字符"
- [ ] 7.3.4 校验失败 → 400 + 错误详情
- [ ] 7.3.5 写文件后 `init_skill_registry()` 重新加载能找到新 skill

---

## 8. 现有端点兼容性

- [ ] 8.1 `/chat` / `/chat/stream` / `/chat/confirm` / `/api/approval/*` / `/api/mcp/*` 行为不变
- [ ] 8.2 新增端点独立路由（不修改现有签名）
