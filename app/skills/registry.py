"""Skill registry: intent pattern matching and lookup."""
import re
import logging
from typing import Optional, Dict, List

from app.skills.loader import SkillConfig, SkillLoader

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Skill registration and intent matching service.

    Intent matching priority: first registered skill with a matching pattern wins.
    ZH patterns are case-sensitive, EN patterns are case-insensitive.
    """

    def __init__(self):
        self._configs: Dict[str, SkillConfig] = {}
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}

    def load_from_loader(self, loader: SkillLoader) -> None:
        """Copy configs from loader and compile all intent patterns."""
        self._configs = loader.get_configs()
        self._compile_all_patterns()
        logger.info(f"SkillRegistry loaded {len(self._configs)} skills")

    def _compile_all_patterns(self) -> None:
        """Compile intent_patterns.zh and intent_patterns.en regexes.

        Invalid patterns are logged and skipped; other patterns still work.
        """
        self._compiled_patterns.clear()
        for name, config in self._configs.items():
            patterns: List[re.Pattern] = []
            for p in config.intent_patterns.get("zh", []):
                try:
                    patterns.append(re.compile(p))
                except re.error:
                    logger.warning(f"Invalid ZH pattern in skill {name}: {p!r}")
            for p in config.intent_patterns.get("en", []):
                try:
                    patterns.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    logger.warning(f"Invalid EN pattern in skill {name}: {p!r}")
            self._compiled_patterns[name] = patterns

    def match_skill(self, message: str) -> Optional[SkillConfig]:
        """Return the first skill whose intent pattern matches the message.

        Iterates skills in registration order. First match wins.
        """
        for name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(message):
                    logger.info(f"Skill matched: {name} for message: {message[:50]}...")
                    return self._configs[name]
        return None

    def get_skill(self, name: str) -> Optional[SkillConfig]:
        return self._configs.get(name)

    def get_all_skills(self) -> Dict[str, SkillConfig]:
        return self._configs

    def add_skill(self, config: SkillConfig) -> None:
        """Hot-add a skill (e.g., after /api/skills/create). Recompiles patterns."""
        self._configs[config.name] = config
        self._compile_all_patterns()
        logger.info(f"Hot-added skill: {config.name}")

    def get_prompt_fragments(self, skill_names: List[str]) -> str:
        """Concatenate prompt_fragment from multiple skills with double-newline."""
        fragments: List[str] = []
        for name in skill_names:
            config = self._configs.get(name)
            if config and config.prompt_fragment:
                fragments.append(config.prompt_fragment)
        return "\n\n".join(fragments)


# Global singleton
_registry: Optional[SkillRegistry] = None


def init_skill_registry() -> SkillRegistry:
    """Initialize the global SkillRegistry singleton.

    Scans skills/ and skills_custom/ on first call. Subsequent calls return cached.
    """
    global _registry
    loader = SkillLoader()
    loader.load_all()
    _registry = SkillRegistry()
    _registry.load_from_loader(loader)
    return _registry


def get_skill_registry() -> Optional[SkillRegistry]:
    """Return the current global SkillRegistry, or None if not initialized."""
    return _registry
