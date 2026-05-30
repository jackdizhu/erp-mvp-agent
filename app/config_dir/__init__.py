import os
import logging
from pathlib import Path
from typing import Dict, Any

import yaml

DEFAULT_PROMPTS = {
    "role": "你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。",
    "capabilities_header": "你可以执行以下操作：",
    "capabilities_footer": "",
    "risk_notice": "对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。",
    "response_style": "请用简洁专业的中文回复用户。",
}


def load_prompts() -> Dict[str, Any]:
    config_path = Path(__file__).parent / "prompts.yaml"

    if not config_path.exists():
        logging.warning(f"Prompt config not found at {config_path}, using defaults")
        return DEFAULT_PROMPTS.copy()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        prompts = data.get("system_prompt", {}) if data else {}

        result = {
            "role": prompts.get("role", DEFAULT_PROMPTS["role"]),
            "capabilities_header": prompts.get("capabilities_header", DEFAULT_PROMPTS["capabilities_header"]),
            "capabilities_footer": prompts.get("capabilities_footer", DEFAULT_PROMPTS["capabilities_footer"]),
            "risk_notice": prompts.get("risk_notice", DEFAULT_PROMPTS["risk_notice"]),
            "response_style": prompts.get("response_style", DEFAULT_PROMPTS["response_style"]),
        }
        return result

    except yaml.YAMLError as e:
        logging.error(f"Failed to parse prompts.yaml: {e}")
        return DEFAULT_PROMPTS.copy()
    except Exception as e:
        logging.error(f"Failed to load prompts.yaml: {e}")
        return DEFAULT_PROMPTS.copy()


__all__ = ["load_prompts", "DEFAULT_PROMPTS"]