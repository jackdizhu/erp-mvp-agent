# Tasks: skill-custom-storage

> 对应 spec: [skill-custom-storage](../specs/skill-custom-storage/spec.md)
> 覆盖原 tasks.md 组 1.2 / 1.5 / 组 16（custom skill 持久化）

## 改动范围

| 文件 | 状态 | 说明 |
|------|------|------|
| `skills_custom/` | 新建 | 项目根目录扁平结构，`.gitignore` 忽略 |
| `skills_custom/.gitkeep` | 新建 | 占位 + 文档说明 |
| `.gitignore` | 修改 | 添加 `skills_custom/` |
| `app/main.py` | 修改 | 写入路径改为 `skills_custom/` 而非 `skills/custom/` |
| `app/skills/loader.py` | 修改 | 扫描路径增加 `skills_custom/` |
| `skills_custom/batch-query-order/skill.yaml` | 新建 | 示例 custom skill |

---

## 1. 目录创建

### 1.1 物理目录
- [ ] 1.1.1 在项目根创建 `skills_custom/` 目录
- [ ] 1.1.2 在 `skills_custom/` 创建 `batch-query-order/` 子目录（示例）
- [ ] 1.1.3 关键决策（决策 4）：**扁平**结构，**不**嵌套 `skills/custom/`

### 1.2 .gitignore
- [ ] 1.2.1 编辑项目根 `.gitignore`，添加 `skills_custom/` 一行
- [ ] 1.2.2 添加 `!skills_custom/.gitkeep` 例外（让占位文件入库）
- [ ] 1.2.3 验证：`git status` 创建 custom skill 后**不**显示为 untracked

### 1.3 占位文档
- [ ] 1.3.1 创建 `skills_custom/.gitkeep` 写入简短说明（"此目录由 Skill 框架运行时使用，存放用户自定义 skill"）

---

## 2. Loader 扫描路径修改

### 2.1 `app/skills/loader.py:SkillLoader.load_all`
- [ ] 2.1.1 新增常量 `_SKILLS_CUSTOM_DIR = _PROJECT_ROOT / "skills_custom"`
- [ ] 2.1.2 在 `load_all` 中新增分支：扫描 `_SKILLS_CUSTOM_DIR` 直接子目录
- [ ] 2.1.3 子目录以 `_` 开头跳过（如 `batch-query-order/` 不跳过）
- [ ] 2.1.4 每个子目录读 `skill.yaml`，注册到 `self._configs[name]`
- [ ] 2.1.5 logger.info 区分 `"Loaded custom skill: {name}"` vs `"Loaded skill: {name}"`

### 2.2 缺失目录处理
- [ ] 2.2.1 `_SKILLS_CUSTOM_DIR.exists() is False` → `logger.warning(...)` + 跳过（**不**抛异常）
- [ ] 2.2.2 preset 目录缺失同理

---

## 3. `app/main.py` 写入路径

### 3.1 路径常量
- [ ] 3.1.1 在 `app/main.py` 顶部新增 `_PROJECT_ROOT = Path(__file__).resolve().parents[1]`
- [ ] 3.1.2 修改 `skill_create` 端点的写入路径：`skill_dir = _PROJECT_ROOT / "skills_custom" / req.name`
- [ ] 3.1.3 关键点：**不**是 `_PROJECT_ROOT / "skills" / "custom" / req.name`（避免与方案 C 文档的嵌套结构混淆）

### 3.2 关键检查
- [ ] 3.2.1 grep 验证 `app/main.py` 中**无** `"skills" / "custom"` 路径
- [ ] 3.2.2 验证 `mkdir(parents=True, exist_ok=True)` 在写入前执行

---

## 4. 示例 Custom Skill

### 4.1 `skills_custom/batch-query-order/skill.yaml`
- [ ] 4.1.1 字段：`name: batch-query-order` / `version: "1.0"` / `description: 批量查询订单状态` / `category: custom`
- [ ] 4.1.2 `intent_patterns.zh`: `["批量.*查询.*订单", "多个.*订单.*状态", "几个.*订单"]`
- [ ] 4.1.3 `intent_patterns.en`: `["batch.*query.*order", "multiple.*order.*status"]`
- [ ] 4.1.4 `tools: [query_order]`
- [ ] 4.1.5 `prompt_fragment`: "批量查询时请逐个查询并汇总为表格"
- [ ] 4.1.6 `workflow.steps:`
  - `parse_input` (type: prompt, instruction: "从用户消息中提取所有订单号，返回 JSON 数组")
  - `batch_query` (type: tool_call, tool: query_order, params: {order_id: "{{parse_input.items[*].order_id}}"}, iterate: true, output: order_results)
  - `summarize` (type: prompt, instruction: "将查询结果整理为表格，包含订单号、状态、收货地址、预计送达时间")

### 4.2 加载验证
- [ ] 4.2.1 重启后 `GET /api/skills/available` 包含 `batch-query-order`
- [ ] 4.2.2 发送 `POST /chat "批量查询订单 ORD-001 ORD-002 ORD-003 状态"` 触发 YAML workflow
- [ ] 4.2.3 验证 `query_order` 被调用 3 次

---

## 5. 安全：custom 不允许 handler.py

- [ ] 5.1 `validator.validate_skill_dir(skill_dir, is_custom=True)` 发现 `handler.py` 报错
- [ ] 5.2 `validator.validate_config` 在 `category=custom` 时 `workflow.handler` 报错
- [ ] 5.3 双层防护：目录级 + 配置级
