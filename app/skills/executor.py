"""Skill executor: dispatches Python handler or YAML workflow."""
import re
import logging
from typing import Optional, Dict, Any, List, Callable

from app.skills.base import SkillHandler, WorkflowResult, WorkflowStep
from app.skills.loader import SkillConfig

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Execute a skill workflow.

    Priority (decision D3):
    1. Python handler (preset skill) if has_handler() is True
    2. YAML workflow (custom or preset-without-handler) if has_yaml_workflow() is True
    3. None (prompt-injection only, LLM handles tool calling)
    """

    def execute(
        self,
        skill: SkillConfig,
        message: str,
        context: dict,
        available_tools: Optional[List[str]] = None,
        on_step_complete: Optional[Callable] = None,
    ) -> Optional[WorkflowResult]:
        """Dispatch to the appropriate execution path.

        Args:
            on_step_complete: Optional callback invoked after each YAML step
                finishes. Signature: (step_def, status, result, error, elapsed_ms).
                Used by SkillObservability for SSE + log emission (design D9).
        """
        if skill.has_handler():
            return self._execute_handler(skill, message, context)

        if skill.has_yaml_workflow():
            steps = skill.get_workflow_steps()
            if steps:
                return self._execute_yaml_workflow(
                    steps, message, context, available_tools or [], on_step_complete
                )

        logger.info(f"Skill {skill.name} has no workflow, prompt injection only")
        return None

    def _execute_handler(
        self, skill: SkillConfig, message: str, context: dict
    ) -> Optional[WorkflowResult]:
        """Execute the Python handler, wrapping exceptions as failure result."""
        try:
            result = skill.handler.execute(message, context)
            logger.info(f"Skill {skill.name} handler executed: success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Skill {skill.name} handler failed: {e}")
            return WorkflowResult(success=False, error=str(e))

    def _execute_yaml_workflow(
        self,
        steps: List[Dict],
        message: str,
        context: dict,
        available_tools: List[str],
        on_step_complete: Optional[Callable] = None,
    ) -> WorkflowResult:
        """Execute a YAML-defined workflow.

        Each step is either:
        - type=tool_call: invoke client_factory.execute_tool
        - type=prompt: record instruction for LLM processing

        on_step_complete is invoked after each step finishes (status='completed'
        or 'failed'). Used by SkillObservability for SSE + audit log.
        """
        import time
        from app.clients.client_factory import client_factory

        def _emit_step(step_def, status, result=None, error=None, elapsed_ms=0):
            """Inner helper to invoke on_step_complete safely (decision D9)."""
            if on_step_complete is None:
                return
            try:
                on_step_complete(step_def, status, result, error, elapsed_ms)
            except Exception as e:
                logger.warning(f"on_step_complete callback failed: {e}")

        steps_result: List[WorkflowStep] = []
        step_outputs: Dict[str, Any] = {"message": message}

        for step_def in steps:
            step_id = step_def.get("id", "unknown")
            step_type = step_def.get("type")
            step_start = time.monotonic()

            if step_type == "tool_call":
                raw_params = step_def.get("params", {})
                resolved_params = self._resolve_params(raw_params, step_outputs)
                tool_name = step_def.get("tool", "")

                if step_def.get("iterate", False):
                    result = self._execute_iterative(
                        step_id, tool_name, resolved_params, client_factory
                    )
                    elapsed_ms = int((time.monotonic() - step_start) * 1000)
                    _emit_step(step_def, "completed", result=result, elapsed_ms=elapsed_ms)
                else:
                    try:
                        result = client_factory.execute_tool(tool_name, resolved_params)
                        elapsed_ms = int((time.monotonic() - step_start) * 1000)
                        _emit_step(step_def, "completed", result=result, elapsed_ms=elapsed_ms)
                    except Exception as e:
                        elapsed_ms = int((time.monotonic() - step_start) * 1000)
                        _emit_step(step_def, "failed", error=str(e), elapsed_ms=elapsed_ms)
                        steps_result.append(WorkflowStep(
                            id=step_id, tool=tool_name,
                            status="failed", error=str(e)
                        ))
                        return WorkflowResult(
                            success=False,
                            error=f"步骤 '{step_id}' 执行失败: {e}",
                            steps=steps_result,
                        )

                steps_result.append(WorkflowStep(
                    id=step_id, tool=tool_name,
                    result=result, status="completed"
                ))

                output_var = step_def.get("output")
                if output_var:
                    step_outputs[output_var] = result

            elif step_type == "prompt":
                elapsed_ms = int((time.monotonic() - step_start) * 1000)
                _emit_step(
                    step_def, "completed",
                    result={"instruction": step_def.get("instruction", "")},
                    elapsed_ms=elapsed_ms,
                )
                steps_result.append(WorkflowStep(
                    id=step_id, tool="prompt",
                    status="completed",
                    result={"instruction": step_def.get("instruction", "")}
                ))

            else:
                logger.warning(f"Unknown step type '{step_type}' in step '{step_id}', skipping")

        return WorkflowResult(
            success=True,
            steps=steps_result,
            intermediate_data=step_outputs,
        )

    def _resolve_params(self, params: Dict, step_outputs: Dict) -> Dict:
        """Recursively resolve {{...}} variable references in string param values."""
        if not params:
            return params
        resolved: Dict = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self._replace_variables(value, step_outputs)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, step_outputs)
            else:
                resolved[key] = value
        return resolved

    def _replace_variables(self, template: str, step_outputs: Dict) -> str:
        """Replace {{step_id.field}} or {{message}} in template.

        Missing variables resolve to empty string (no exception).
        """
        def replacer(match: "re.Match") -> str:
            var_path = match.group(1).strip()
            if var_path == "message":
                return step_outputs.get("message", "")

            # step_id.path or step_id.items[*].field
            parts = var_path.split(".", 1)
            if len(parts) == 2:
                step_id, path = parts
                step_data = step_outputs.get(step_id, {})
                return self._get_nested(step_data, path)

            return match.group(0)

        return re.sub(r'\{\{(.+?)\}\}', replacer, template)

    def _get_nested(self, data: Any, path: str) -> str:
        """Navigate nested dict/list using dot-split path with [*] strip."""
        parts = path.replace("[*]", "").split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, "")
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else ""
            else:
                return str(current)
        return str(current) if current is not None else ""

    def _execute_iterative(
        self, step_id: str, tool: str, params: Dict, client_factory
    ) -> List:
        """Execute a tool once per element of an array param.

        Detects list values in resolved params, treats the first list as the
        iteration source. Singular key name is derived by stripping trailing 's'.
        """
        results: List = []
        # Find the first list-valued param to iterate over
        for key, value in params.items():
            if isinstance(value, list):
                singular_key = key.rstrip("s")
                for item in value:
                    item_params = {k: v for k, v in params.items() if k != key}
                    item_params[singular_key] = item
                    try:
                        result = client_factory.execute_tool(tool, item_params)
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e)})
                return results

        # No list found: fall through to single call
        result = client_factory.execute_tool(tool, params)
        return [result]
