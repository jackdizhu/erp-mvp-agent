"""Skill validator: field checks, tool availability, workflow validation, security."""
import re
import logging
from typing import List, Tuple, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Blacklist patterns for custom skill security (decision D9).
# Each pattern uses re.IGNORECASE for case-insensitive matching.
# Patterns are designed to catch natural language variants (e.g., "调用 http 接口",
# "read a file", "import a module") regardless of keyword order.
FORBIDDEN_PATTERNS = [
    # File I/O: "read file", "write file", "文件读写", "读文件", "写文件"
    re.compile(r'(?:file|文件)\s*(?:read|write|读写|读取|写入|操作|访问)', re.IGNORECASE),
    re.compile(r'(?:读|写|访问|操作|打开)\s*(?:file|文件)', re.IGNORECASE),
    # HTTP/network calls: "call http", "调用接口", "http request", "fetch api"
    re.compile(r'(?:http|fetch|request|api|接口|url)\s*(?:call|request|请求|调用|访问|操作)', re.IGNORECASE),
    re.compile(r'(?:调用|请求|访问|操作)\s*(?:http|fetch|request|api|接口|url|网络|外部)', re.IGNORECASE),
    # Forwarding/proxy
    re.compile(r'(?:forward|proxy|转发|代理|中转)', re.IGNORECASE),
    # Code execution
    re.compile(r'(?:exec|eval|system|subprocess|os\.|popen|spawn|shell)', re.IGNORECASE),
    # Dynamic imports
    re.compile(r'(?:^import\s|\bfrom\s+\w+\s+import\b)', re.IGNORECASE),
]


def _strip_mcp_prefix(tools: List[str]) -> List[str]:
    """Remove 'mcp_' prefix from each tool name to match skill.yaml short names.

    client_factory.get_all_tools() returns names that may have already been
    stripped (at registration), so this is idempotent.
    """
    return [t[4:] if t.startswith("mcp_") else t for t in tools]


class SkillValidator:
    """Validate skill configuration: required fields, workflow, tools, security."""

    def validate_config(
        self,
        config_data: Dict,
        available_tools: List[str],
        is_custom: bool = True,
    ) -> Tuple[bool, List[str]]:
        """Validate a skill.yaml parsed dictionary.

        Args:
            config_data: Result of yaml.safe_load on skill.yaml.
            available_tools: Short tool names from client_factory.get_all_tools().
            is_custom: True for custom skills (applies security blacklist, forbids handler).

        Returns:
            (is_valid, errors) tuple. Empty errors list means valid.
        """
        errors: List[str] = []

        # 1. Basic field validation
        if not config_data.get("name"):
            errors.append("Skill 名称不能为空")
        if not config_data.get("description"):
            errors.append("Skill 描述不能为空")

        # 2. Intent patterns
        patterns = config_data.get("intent_patterns", {})
        if not patterns.get("zh") and not patterns.get("en"):
            errors.append("至少需要定义一种语言的意图匹配规则")

        # 3. Tools
        tools = config_data.get("tools", [])
        if not tools:
            errors.append("Skill 必须声明依赖的工具列表")
        else:
            # Top-level tool existence check (vs available_tools)
            stripped = _strip_mcp_prefix(available_tools)
            for t in tools:
                if t not in stripped:
                    errors.append(
                        f"工具 '{t}' 未在当前 MCP 注册表中，"
                        f"可用工具: {', '.join(stripped)}"
                    )

        # 4. Workflow (if present)
        workflow = config_data.get("workflow")
        if workflow:
            workflow_errors = self._validate_workflow(workflow, available_tools, is_custom)
            errors.extend(workflow_errors)

        # 5. Custom-specific checks
        if is_custom:
            security_errors = self._validate_security(config_data)
            errors.extend(security_errors)

            if workflow and workflow.get("handler"):
                errors.append("自定义 Skill 不允许使用 Python handler，只能使用 YAML 工作流")

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Skill validation failed: {errors}")
        return is_valid, errors

    def _validate_workflow(
        self, workflow: Dict, available_tools: List[str], is_custom: bool
    ) -> List[str]:
        """Validate workflow definition."""
        errors: List[str] = []

        # If has handler, steps are reference only
        if workflow.get("handler"):
            return errors

        # YAML workflow: strict step validation
        steps = workflow.get("steps", [])
        if not steps:
            errors.append("工作流至少需要一个步骤")
            return errors

        stripped_tools = _strip_mcp_prefix(available_tools)
        for i, step in enumerate(steps):
            step_errors = self._validate_step(step, i, stripped_tools)
            errors.extend(step_errors)

        return errors

    def _validate_step(
        self, step: Dict, index: int, available_tools: List[str]
    ) -> List[str]:
        """Validate a single workflow step."""
        errors: List[str] = []
        step_id = step.get("id", f"step_{index}")
        step_type = step.get("type")

        if not step_type:
            errors.append(f"步骤 '{step_id}' 缺少 type 字段")
            return errors

        if step_type == "tool_call":
            tool = step.get("tool")
            if not tool:
                errors.append(f"步骤 '{step_id}' 缺少 tool 字段")
            elif tool not in available_tools:
                errors.append(
                    f"步骤 '{step_id}' 引用了未注册的工具 '{tool}'，"
                    f"可用工具: {', '.join(available_tools)}"
                )

            if not step.get("params"):
                errors.append(f"步骤 '{step_id}' 缺少 params 字段")

        elif step_type == "prompt":
            if not step.get("instruction"):
                errors.append(f"步骤 '{step_id}' 缺少 instruction 字段")

        else:
            errors.append(
                f"步骤 '{step_id}' 类型无效: {step_type}，仅支持 tool_call 和 prompt"
            )

        return errors

    def _validate_security(self, config_data: Dict) -> List[str]:
        """Scan text fields against forbidden patterns (custom skill only)."""
        errors: List[str] = []

        full_text = config_data.get("description", "")
        full_text += " " + config_data.get("prompt_fragment", "")

        # Use `or {}` to handle case where workflow is explicitly None
        workflow = config_data.get("workflow") or {}
        for step in workflow.get("steps", []):
            if step.get("instruction"):
                full_text += " " + step["instruction"]

        for pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(full_text)
            if match:
                errors.append(
                    f"安全校验失败：包含禁止的操作 '{match.group()}'，"
                    f"自定义 Skill 不支持文件读写、接口调用、转发等高风险操作"
                )

        return errors

    def validate_skill_dir(
        self, skill_dir: Path, is_custom: bool = True
    ) -> Tuple[bool, List[str]]:
        """Check skill directory structural integrity."""
        errors: List[str] = []

        yaml_path = skill_dir / "skill.yaml"
        if not yaml_path.exists():
            errors.append("缺少 skill.yaml 配置文件")
            return False, errors

        if is_custom:
            handler_path = skill_dir / "handler.py"
            if handler_path.exists():
                errors.append("自定义 Skill 不允许包含 handler.py 代码文件")

        is_valid = len(errors) == 0
        return is_valid, errors
