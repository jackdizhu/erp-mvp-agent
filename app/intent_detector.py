import os
import re
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_INTENT_RULES_PATH = os.path.join(os.path.dirname(__file__), "config", "intent_rules.json")

BUILTIN_DEFAULT_RULES = {
    "update_order": {
        "zh": ["修改.*订单", "改.*地址", "改.*电话", "更新.*订单", "变更.*订单"],
        "en": ["update.*order", "change.*address", "modify.*order"]
    },
    "cancel_order": {
        "zh": ["取消.*订单", "不要.*订单", "退掉.*订单"],
        "en": ["cancel.*order", "delete.*order", "remove.*order"]
    },
    "delete_order": {
        "zh": ["删除.*订单", "删掉.*订单", "移除.*订单"],
        "en": ["delete.*order", "remove.*order.*permanently"]
    },
    "adjust_inventory": {
        "zh": ["调整.*库存", "修改.*库存", "增加.*库存", "减少.*库存", "补货"],
        "en": ["adjust.*inventory", "update.*stock", "add.*stock"]
    }
}

_intent_rules: Optional[Dict[str, Dict[str, List[str]]]] = None
_rules_path: Optional[str] = None


def _load_rules_from_file(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        if not _validate_rules(rules):
            logger.warning(f"Invalid intent rules structure at {path}, using built-in defaults")
            return None
        return rules
    except FileNotFoundError:
        logger.warning(f"Intent rules file not found at {path}, using built-in defaults")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse intent rules file: {e}, using built-in defaults")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading intent rules: {e}, using built-in defaults")
        return None


def _validate_rules(rules: dict) -> bool:
    if not isinstance(rules, dict):
        return False
    for tool_name, patterns in rules.items():
        if not isinstance(patterns, dict):
            return False
        if "zh" not in patterns or "en" not in patterns:
            return False
        if not isinstance(patterns["zh"], list) or not isinstance(patterns["en"], list):
            return False
    return True


def _compile_patterns(rules: Dict) -> Dict[str, List[re.Pattern]]:
    compiled = {}
    for tool_name, patterns in rules.items():
        compiled[tool_name] = []
        for pattern in patterns.get("zh", []):
            try:
                compiled[tool_name].append(re.compile(pattern))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
        for pattern in patterns.get("en", []):
            try:
                compiled[tool_name].append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
    return compiled


def load_intent_rules() -> None:
    global _intent_rules, _rules_path
    custom_path = os.getenv("INTENT_RULES_PATH")
    rules_path = custom_path if custom_path else DEFAULT_INTENT_RULES_PATH
    _rules_path = rules_path

    rules = _load_rules_from_file(rules_path)
    if rules is None:
        _intent_rules = BUILTIN_DEFAULT_RULES
    else:
        _intent_rules = rules

    logger.info(f"Intent rules loaded from {rules_path}")


def get_intent_rules() -> Dict:
    if _intent_rules is None:
        load_intent_rules()
    return _intent_rules


def reload_intent_rules() -> None:
    global _intent_rules
    logger.info("Reloading intent rules...")
    load_intent_rules()


def detect_tool_intent(message: str) -> Optional[str]:
    if _intent_rules is None:
        load_intent_rules()

    compiled = _compile_patterns(_intent_rules)

    for tool_name, patterns in compiled.items():
        for pattern in patterns:
            if pattern.search(message):
                logger.info(f"Intent detected: {tool_name} for message: {message[:50]}...")
                return tool_name

    return None


def check_approval_status(action_id: str) -> Optional[dict]:
    """检查审批状态，返回 user_op_id 和 approved 如果已决定"""
    from app.approval_store import approval_store
    record = approval_store.get(action_id)
    if record and record.user_op_id:
        return {
            "user_op_id": record.user_op_id,
            "approved": record.approved,
            "action_id": action_id
        }
    return None
