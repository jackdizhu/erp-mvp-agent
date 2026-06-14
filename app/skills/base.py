"""Skill base classes and workflow data structures."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class WorkflowStep:
    """Single step in a skill workflow execution."""
    id: str
    tool: str
    status: str = "pending"  # pending | completed | failed | pending_approval
    args: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class WorkflowResult:
    """Aggregate result of a skill workflow execution.

    Bridge contract (decision D3): when need_approval=True, intermediate_data
    MUST contain three keys: tool, tool_args, approval_summary. The agent layer
    consumes these to call approval_core.create_pending.
    """
    success: bool
    error: Optional[str] = None
    need_more_info: bool = False
    need_approval: bool = False
    intermediate_data: Optional[Dict[str, Any]] = None
    steps: List[WorkflowStep] = field(default_factory=list)


class SkillHandler:
    """Base class for skill workflow handlers (preset skill only).

    Custom skills MUST NOT use Python handlers; they rely on YAML workflow
    executed by SkillExecutor. See skill-approval-bridge spec.
    """

    skill_name: str = ""

    def execute(self, message: str, context: dict) -> WorkflowResult:
        """Execute the skill workflow.

        Args:
            message: User's original message.
            context: Runtime context (client_factory, messages, etc.).

        Returns:
            WorkflowResult describing outcome. Set:
            - success=True, no flags: workflow completed, intermediate_data has results
            - need_more_info=True: ask user for more input
            - need_approval=True: requires user approval (intermediate_data must have
              tool/tool_args/approval_summary)
            - success=False: terminal error
        """
        raise NotImplementedError

    def verify(self, result: WorkflowResult) -> bool:
        """Verify a workflow result. Subclasses may override for custom validation."""
        return result.success
