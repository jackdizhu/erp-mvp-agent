## ADDED Requirements

### Requirement: 工具结果结构化展示
前端 SHALL 提供 DataVizCard 组件，将工具调用结果从原始 JSON 升级为结构化可视化展示。

#### Scenario: 订单数据表格展示
- **WHEN** query_order 返回订单数据
- **THEN** 前端渲染为表格格式，包含订单 ID、状态、商品、金额等字段

#### Scenario: 库存数据卡片展示
- **WHEN** query_inventory 返回库存数据
- **THEN** 前端渲染为库存状态卡片，包含数量、预留、可用量可视化

#### Scenario: 批量查询结果列表展示
- **WHEN** query_orders 返回多个订单数据
- **THEN** 前端渲染为列表格式，每条订单一行摘要
