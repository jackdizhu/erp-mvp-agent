# Tasks: skill-log-events

> 对应 spec: [skill-log-events](../specs/skill-log-events/spec.md)
> 实施阶段: Phase 1（后端 SSE + 日志）

## 改动范围

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `app/agent_logger.py` | 修改 | +~50 | 4 个新方法 `log_skill_matched` / `log_workflow_step` / `log_workflow_result` / `log_skill_failed` + 截断辅助 |

---

## 1. `app/agent_logger.py` 修改

### 1.1 截断辅助函数
- [ ] 1.1.1 新增模块级 `def _truncate(text: str, max_len: int = 200) -> str: return text[:max_len] + "..." if len(text) > max_len else text`
- [ ] 1.1.2 关键点（设计 D7）：仅 `prompt_fragment` 完整记录；其他文本字段（description / instruction / error_detail）截断 200 字符

### 1.2 log_skill_matched 方法
- [ ] 1.2.1 实现 `def log_skill_matched(self, skill_name: str, category: str, has_workflow: bool, has_handler: bool, correlation_id: str, prompt_fragment: str) -> None:`
- [ ] 1.2.2 data 字段：`{skill_name, category, has_workflow, has_handler, correlation_id, prompt_fragment}`（prompt_fragment 完整，不截断）
- [ ] 1.2.3 调 `self._write("skill_matched", data)`
- [ ] 1.2.4 关键点：空 prompt_fragment 也写入（value="" 不省略）

### 1.3 log_workflow_step 方法
- [ ] 1.3.1 实现 `def log_workflow_step(self, correlation_id: str, skill_name: str, step_id: str, type: str, status: str, tool: Optional[str]=None, instruction: Optional[str]=None, result: Optional[dict]=None, error: Optional[str]=None) -> None:`
- [ ] 1.3.2 data 字段：`{correlation_id, skill_name, step_id, type, status, tool?, instruction? (截断 200), result?, error?}`
- [ ] 1.3.3 关键点：instruction 必截断（即使 50 字符也截断，保持一致性）

### 1.4 log_workflow_result 方法
- [ ] 1.4.1 实现 `def log_workflow_result(self, correlation_id: str, skill_name: str, success: bool, need_approval: bool, need_more_info: bool, step_count: int) -> None:`
- [ ] 1.4.2 data 字段：`{correlation_id, skill_name, success, need_approval, need_more_info, step_count}`

### 1.5 log_skill_failed 方法
- [ ] 1.5.1 实现 `def log_skill_failed(self, correlation_id: str, skill_name: str, error_code: str, error_detail: str, failed_step_id: Optional[str]=None) -> None:`
- [ ] 1.5.2 data 字段：`{correlation_id, skill_name, error_code, error_detail (截断 200), failed_step_id?}`
- [ ] 1.5.3 截断 error_detail 200 字符（避免长堆栈污染日志）

### 1.6 单元测试（≤ 1 小时）
- [ ] 1.6.1 5 个方法各调一次，断言写入的 entry 字段
- [ ] 1.6.2 验证 prompt_fragment 不截断（600 字符完整保留）
- [ ] 1.6.3 验证 instruction 截断 200 字符
- [ ] 1.6.4 验证 error_detail 截断 200 字符
- [ ] 1.6.5 验证 log 写入失败时 `_write` 内部 try/except 兜底（已有行为）
