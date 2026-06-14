"""Skill loader: scan skills/ and skills_custom/ directories, load skill.yaml."""
import sys
import yaml
import logging
import importlib
from pathlib import Path
from typing import Dict, Optional, List

from app.skills.base import SkillHandler

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _PROJECT_ROOT / "skills"
_SKILLS_CUSTOM_DIR = _PROJECT_ROOT / "skills_custom"


class SkillConfig:
    """Configuration for a single skill loaded from skill.yaml."""

    def __init__(self, name: str, config_path: Path):
        self.name = name
        self.config_path = config_path
        self.version = "1.0"
        self.description = ""
        self.category = "preset"  # preset | custom
        self.intent_patterns = {"zh": [], "en": []}
        self.tools: List[str] = []
        self.prompt_fragment = ""
        self.workflow = None  # dict or None
        self.handler: Optional[SkillHandler] = None
        self._loaded = False

    def load(self) -> bool:
        """Read skill.yaml and populate fields. Returns False on any error."""
        yaml_path = self.config_path / "skill.yaml"
        if not yaml_path.exists():
            logger.warning(f"skill.yaml not found in {self.config_path}")
            return False

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            self.version = data.get("version", "1.0")
            self.description = data.get("description", "")
            self.category = data.get("category", "preset")
            self.intent_patterns = data.get("intent_patterns", {"zh": [], "en": []})
            self.tools = data.get("tools", [])
            self.prompt_fragment = data.get("prompt_fragment", "")
            self.workflow = data.get("workflow")

            # Load Python handler if specified (preset only)
            if self.workflow and self.workflow.get("handler"):
                self._load_handler(self.workflow["handler"])

            self._loaded = True
            logger.info(f"Loaded skill: {self.name} (category={self.category})")
            return True

        except Exception as e:
            logger.error(f"Failed to load skill {self.name}: {e}")
            return False

    def _load_handler(self, handler_path: str) -> None:
        """Dynamically load a Python handler class.

        handler_path format: "module_name.ClassName"
        Module is imported from self.config_path (which is added to sys.path).
        """
        parts = handler_path.rsplit(".", 1)
        if len(parts) != 2:
            logger.error(f"Invalid handler path: {handler_path}")
            return

        module_name, class_name = parts
        handler_dir = self.config_path

        try:
            if str(handler_dir) not in sys.path:
                sys.path.insert(0, str(handler_dir))
            module = importlib.import_module(module_name)
            handler_class = getattr(module, class_name)
            self.handler = handler_class()
            logger.info(f"Loaded handler {handler_path} for skill {self.name}")
        except Exception as e:
            logger.error(f"Failed to load handler {handler_path}: {e}")

    def get_workflow_steps(self) -> List[Dict]:
        """Get workflow steps list from skill.yaml's workflow.steps."""
        if not self.workflow:
            return []
        return self.workflow.get("steps", [])

    def has_handler(self) -> bool:
        """Whether this skill has a Python handler attached."""
        return self.handler is not None

    def has_yaml_workflow(self) -> bool:
        """Whether this skill has a YAML workflow (no Python handler)."""
        return self.workflow is not None and not self.has_handler()


class SkillLoader:
    """Scan and load all skills from the configured root directories."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self._skills_dir = skills_dir or _SKILLS_DIR
        self._configs: Dict[str, SkillConfig] = {}

    def load_all(self) -> Dict[str, SkillConfig]:
        """Scan skills/ and skills_custom/, load all skill.yaml files."""
        # Scan preset skills
        if self._skills_dir.exists():
            for item in self._skills_dir.iterdir():
                if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("."):
                    yaml_path = item / "skill.yaml"
                    if yaml_path.exists():
                        config = SkillConfig(name=item.name, config_path=item)
                        if config.load():
                            self._configs[item.name] = config
        else:
            logger.warning(f"Skills directory not found: {self._skills_dir}")

        # Scan custom skills (flat directory, decision D4)
        if _SKILLS_CUSTOM_DIR.exists():
            for item in _SKILLS_CUSTOM_DIR.iterdir():
                if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("."):
                    yaml_path = item / "skill.yaml"
                    if yaml_path.exists():
                        config = SkillConfig(name=item.name, config_path=item)
                        if config.load():
                            self._configs[item.name] = config
                            logger.info(f"Loaded custom skill: {item.name}")
        else:
            logger.warning(f"Custom skills directory not found: {_SKILLS_CUSTOM_DIR} (will be created on first /api/skills/create)")

        return self._configs

    def get_configs(self) -> Dict[str, SkillConfig]:
        return self._configs

    def reload(self) -> Dict[str, SkillConfig]:
        """Clear and re-scan all directories. Used for hot-reload scenarios."""
        self._configs.clear()
        return self.load_all()
