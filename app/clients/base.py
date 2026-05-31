from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseClient(ABC):
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_risk_level(self, tool_name: str) -> str:
        pass

    @abstractmethod
    def execute_tool(self, name: str, args: dict) -> dict:
        pass

    @abstractmethod
    def get_approval_detail(self, tool_name: str, args: dict) -> dict:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass