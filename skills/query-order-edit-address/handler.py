"""修改订单收货地址 - 工作流编排 (handler for query-order-edit-address).

Bridge contract (decision D3): this handler does NOT import approval_core.
It returns WorkflowResult with intermediate_data containing tool/tool_args/
approval_summary; the agent layer (_handle_skill_approval) bridges to
approval_core.create_pending.
"""
import re
import logging

from app.skills.base import SkillHandler, WorkflowStep, WorkflowResult

logger = logging.getLogger(__name__)


class OrderEditAddressHandler(SkillHandler):
    """Query-then-update workflow: get current address, confirm, modify, verify.

    Return values:
    - need_more_info=True: missing new address; agent should ask user
    - need_approval=True: full info present; agent should request approval
    """

    skill_name = "query-order-edit-address"

    def execute(self, message: str, context: dict) -> WorkflowResult:
        # Lazy import to avoid circular dependency at module load time
        from app.clients.client_factory import client_factory

        # Step 1: extract order_id
        order_id = self._extract_order_id(message)
        if not order_id:
            return WorkflowResult(
                success=False,
                error="无法从消息中识别订单号，请提供订单编号",
                steps=[],
            )

        # Step 2: query current order
        try:
            current_order = client_factory.execute_tool(
                "query_order", {"order_id": order_id}
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"查询订单失败: {e}",
                steps=[],
            )

        # Extract current address (defensive: handle missing data)
        data = current_order.get("data", {}) if isinstance(current_order, dict) else {}
        current_address = data.get("address", "未知") if isinstance(data, dict) else "未知"

        # Step 3: extract new address
        new_address = self._extract_new_address(message)
        if not new_address:
            # Missing new address: ask user
            return WorkflowResult(
                success=True,
                need_more_info=True,
                intermediate_data={
                    "order_id": order_id,
                    "current_address": current_address,
                    "message": f"当前收货地址为：{current_address}，请提供新地址",
                },
                steps=[
                    WorkflowStep(
                        id="query_current", tool="query_order",
                        result=current_order, status="completed"
                    )
                ],
            )

        # Step 4: return approval contract (agent will bridge to approval_core)
        return WorkflowResult(
            success=True,
            need_approval=True,
            intermediate_data={
                "tool": "update_order",
                "tool_args": {
                    "order_id": order_id,
                    "field": "address",
                    "value": new_address,
                },
                "approval_summary": (
                    f"修改订单 {order_id} 收货地址：{current_address} → {new_address}"
                ),
            },
            steps=[
                WorkflowStep(
                    id="query_current", tool="query_order",
                    result=current_order, status="completed"
                ),
                WorkflowStep(
                    id="confirm_and_update", tool="update_order",
                    status="pending_approval",
                    args={"order_id": order_id, "field": "address", "value": new_address},
                ),
            ],
        )

    def _extract_order_id(self, message: str) -> str:
        """Extract order ID from user message via regex patterns."""
        patterns = [
            r'ORD[-_]?\d+',
            r'订单\s*号?[：:]\s*(\S+)',
            r'订单\s+(\S+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)
        return ""

    def _extract_new_address(self, message: str) -> str:
        """Extract new address from user message."""
        patterns = [
            r'(?:改成|改为|换成|修改为|更新为)\s*(.+?)(?:$|。|，)',
            r'(?:地址|收货地址)[是为]\s*(.+?)(?:$|。|，)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1).strip()
        return ""
