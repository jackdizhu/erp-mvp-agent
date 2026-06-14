"""Skill observability: emit SSE events + write log entries for Skill execution.

Encapsulates the correlation_id lifecycle, SSE event emission, and audit log
writes. Used by agent.py to surface Skill behavior to the frontend and jsonl log.

Decision D1: A single SkillObservability instance per Skill execution holds the
correlation_id used across all emitted events/log entries.
"""
import logging
import uuid
from typing import Optional, Dict, Any, Callable

from app.skills.loader import SkillConfig
from app.skills.base import WorkflowResult, WorkflowStep

logger = logging.getLogger(__name__)


class SkillObservability:
    """Per-execution observability context for a matched Skill.

    Created when a skill is matched; held for the duration of one execution;
    discarded after workflow_result / skill_failed emit.
    """

    def __init__(
        self,
        skill: SkillConfig,
        logger=None,
        on_event: Optional[Callable[[str, Dict], None]] = None,
    ):
        # Decision D2: 12 hex chars (48-bit entropy) — sufficient uniqueness, compact
        self.correlation_id: str = f"skill_exec_{uuid.uuid4().hex[:12]}"
        self.skill_name: str = skill.name
        self.category: str = skill.category
        self.has_workflow: bool = skill.workflow is not None
        self.has_handler: bool = skill.has_handler()
        self.tools: list = list(skill.tools or [])
        self.description: str = skill.description or ""
        self._logger = logger
        self._on_event = on_event
        self._step_count: int = 0
        self._failed_step_id: Optional[str] = None

    # ---------- internals ----------

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an SSE event. Exceptions are caught and logged (do not break main flow)."""
        if self._on_event is None:
            return
        try:
            payload = {**data, "correlation_id": self.correlation_id}
            self._on_event(event_type, payload)
        except Exception as e:
            logger.warning(f"SkillObservability: failed to emit {event_type}: {e}")

    def _log(self, method: str, **kwargs) -> None:
        """Call logger method if logger is set. Exceptions caught."""
        if self._logger is None:
            return
        try:
            getattr(self._logger, method)(**kwargs)
        except Exception as e:
            logger.warning(f"SkillObservability: failed to log via {method}: {e}")

    # ---------- public API ----------

    def skill_matched(self, prompt_fragment: str = "") -> None:
        """Emit skill_matched SSE + log entry. Called once per execution, BEFORE executor."""
        self._emit("skill_matched", {
            "name": self.skill_name,
            "category": self.category,
            "description": self.description,
            "tools": self.tools,
            "has_workflow": self.has_workflow,
            "has_handler": self.has_handler,
        })
        self._log("log_skill_matched",
                  skill_name=self.skill_name,
                  category=self.category,
                  has_workflow=self.has_workflow,
                  has_handler=self.has_handler,
                  correlation_id=self.correlation_id,
                  prompt_fragment=prompt_fragment or "")

    def workflow_step(
        self,
        step_id: str,
        type: str,
        status: str,
        tool: Optional[str] = None,
        instruction: Optional[str] = None,
        elapsed_ms: Optional[int] = None,
        result_summary: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Emit workflow_step SSE + log entry. Called per step completion.

        Decision D4: only emit when status is completed/failed/pending_approval,
        NOT for pending/in-progress states.
        """
        if status == "completed":
            self._step_count += 1
        if status == "failed":
            self._failed_step_id = step_id

        data: Dict[str, Any] = {
            "step_id": step_id,
            "type": type,
            "status": status,
        }
        if tool is not None:
            data["tool"] = tool
        if instruction is not None:
            data["instruction"] = instruction
        if elapsed_ms is not None:
            data["elapsed_ms"] = elapsed_ms
        if result_summary is not None:
            data["result_summary"] = result_summary

        self._emit("workflow_step", data)
        self._log("log_workflow_step",
                  correlation_id=self.correlation_id,
                  skill_name=self.skill_name,
                  step_id=step_id,
                  type=type,
                  status=status,
                  tool=tool,
                  instruction=instruction,
                  result={"summary": result_summary} if result_summary else None,
                  error=error)

    def workflow_result(
        self,
        success: bool,
        need_approval: bool = False,
        need_more_info: bool = False,
        step_count: Optional[int] = None,
    ) -> None:
        """Emit workflow_result SSE + log entry. Called after executor returns success."""
        count = step_count if step_count is not None else self._step_count
        self._emit("workflow_result", {
            "success": success,
            "need_approval": need_approval,
            "need_more_info": need_more_info,
            "step_count": count,
        })
        self._log("log_workflow_result",
                  correlation_id=self.correlation_id,
                  skill_name=self.skill_name,
                  success=success,
                  need_approval=need_approval,
                  need_more_info=need_more_info,
                  step_count=count)

    def skill_failed(
        self,
        error_code: str,
        error_detail: str,
        failed_step_id: Optional[str] = None,
    ) -> None:
        """Emit skill_failed SSE + log entry. Called when executor fails."""
        if failed_step_id is not None:
            self._failed_step_id = failed_step_id

        data: Dict[str, Any] = {
            "name": self.skill_name,
            "error_code": error_code,
            "error_detail": error_detail,
        }
        if self._failed_step_id is not None:
            data["failed_step_id"] = self._failed_step_id

        self._emit("skill_failed", data)
        self._log("log_skill_failed",
                  correlation_id=self.correlation_id,
                  skill_name=self.skill_name,
                  error_code=error_code,
                  error_detail=error_detail,
                  failed_step_id=self._failed_step_id)
