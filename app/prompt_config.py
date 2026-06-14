import os
import logging
from pathlib import Path
from typing import Dict, Any, List

from app.config_dir import load_prompts, DEFAULT_PROMPTS

_loaded_prompts: Dict[str, Any] = None


def _get_prompts() -> Dict[str, Any]:
    global _loaded_prompts
    if _loaded_prompts is None:
        _loaded_prompts = load_prompts()
    return _loaded_prompts


def build_capabilities_list(tools: List[dict]) -> str:
    if not tools:
        return ""

    lines = []
    for tool in tools:
        func = tool.get("function", {})
        desc = func.get("description", "")
        if desc:
            lines.append(f"- {desc}")

    return "\n".join(lines)


def build_system_prompt(skill_fragments: str = "") -> str:
    prompts = _get_prompts()

    from erp_app.tools import TOOL_SCHEMAS
    capabilities = build_capabilities_list(TOOL_SCHEMAS)

    role = prompts.get("role", DEFAULT_PROMPTS["role"])
    capabilities_header = prompts.get("capabilities_header", DEFAULT_PROMPTS["capabilities_header"])
    capabilities_footer = prompts.get("capabilities_footer", DEFAULT_PROMPTS["capabilities_footer"])
    risk_notice = prompts.get("risk_notice", DEFAULT_PROMPTS["risk_notice"])
    response_style = prompts.get("response_style", DEFAULT_PROMPTS["response_style"])

    parts = [role]

    if capabilities:
        parts.append("")
        parts.append(capabilities_header)
        parts.append(capabilities)
        if capabilities_footer:
            parts.append(capabilities_footer)

    parts.append("")
    parts.append(risk_notice)
    parts.append(response_style)

    # Skill injection (decision D2)
    if skill_fragments:
        parts.append("")
        parts.append("=== 技能指引 ===")
        parts.append(skill_fragments)

    return "\n".join(parts)


__all__ = ["build_system_prompt", "build_capabilities_list"]