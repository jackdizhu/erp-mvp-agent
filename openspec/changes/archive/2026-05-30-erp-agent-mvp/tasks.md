## Task Index

详细任务已按 Spec 能力拆分为独立文件，每个文件包含具体实现代码片段。

### 基础设施（无独立 spec，需首先完成）

- [x] 0.1 Initialize FastAPI backend: create `/app` with `__init__.py`, add `requirements.txt` (fastapi, uvicorn, openai, pydantic)
- [x] 0.2 Initialize React + Vite frontend: `npm create vite@latest frontend -- --template react`
- [x] 0.3 Configure environment variables: `.env` with `OPENAI_API_KEY`, `LLM_MODEL`

### 按依赖顺序实施

| 顺序 | Spec | Task 文件 | 任务数 | 依赖 |
|------|------|----------|--------|------|
| 1 | mock-erp | [specs/mock-erp/tasks.md](specs/mock-erp/tasks.md) | 6 | 无 |
| 2 | error-handling | [specs/error-handling/tasks.md](specs/error-handling/tasks.md) | 3 | 无 |
| 3 | tool-system | [specs/tool-system/tasks.md](specs/tool-system/tasks.md) | 6 | mock-erp, error-handling |
| 4 | approval-flow | [specs/approval-flow/tasks.md](specs/approval-flow/tasks.md) | 7 | tool-system, config |
| 5 | agent-core | [specs/agent-core/tasks.md](specs/agent-core/tasks.md) | 3 | tool-system, approval-flow, llm |
| 6 | chat-api | [specs/chat-api/tasks.md](specs/chat-api/tasks.md) | 3 | agent-core |
| 7 | session-context | [specs/session-context/tasks.md](specs/session-context/tasks.md) | 6 | 无(前端) |
| 8 | chat-ui | [specs/chat-ui/tasks.md](specs/chat-ui/tasks.md) | 5 | session-context, chat-api |

### 集成测试

- [x] 9.1 Scenario 1: query_order — "订单123现在什么状态？" → SAFE → direct reply
- [x] 9.2 Scenario 2: create_order — "为供应商A创建采购订单：iPhone 15 ×3" → CAUTION → limit check → execute
- [x] 9.3 Scenario 3: query_inventory + reasoning — "iPhone 15还有库存吗？能接100台订单吗？" → SAFE → reasoning reply
- [x] 9.4 Scenario 4: exception handling — "订单124为什么还没发货？" → SAFE → explanation with notes
- [x] 9.5 Scenario 5: batch query — "查一下订单123、124、125状态" → SAFE → consolidated reply
- [x] 9.6 Scenario 6: update with approval — "把订单123的收货地址改成北京市朝阳区" → DANGER → approval card → confirm → execute
- [x] 9.7 Scenario 7: cancel with approval — "请取消订单124，原因是库存不足无法发货" → DANGER → approval card → confirm → execute + inventory release
- [x] 9.8 Scenario 8: multi-action approval — 两次独立DANGER操作 → 2 independent cards
