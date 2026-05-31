import logging
from typing import List, Dict, Any, Optional

from app.clients.erp_adapter import get_erp_adapter
from app.config import ENABLE_LOCAL_ADAPTER
from app.errors import tool_not_found

logger = logging.getLogger(__name__)


class ClientFactory:
    def __init__(self):
        self._clients = {}
        self._tool_prefix_map = {}
        self._mcp_tool_alias = {}
        self._erp_adapter = get_erp_adapter()
        self._fallback_registered = False

    def register_client(self, name: str, client):
        self._clients[name] = client
        for tool in client.get_tools():
            tool_name = tool.get("name", "")
            if tool_name:
                self._tool_prefix_map[tool_name] = name
                if tool_name.startswith("mcp_"):
                    original_name = tool_name[4:]
                    self._mcp_tool_alias[original_name] = tool_name

    def register_erp_adapter(self):
        if not self._fallback_registered:
            self._clients["erp_local"] = self._erp_adapter
            for tool in self._erp_adapter.get_tools():
                tool_name = tool.get("name", "")
                if tool_name:
                    self._tool_prefix_map[tool_name] = "erp_local"
            self._fallback_registered = True

    def get_client(self, name: str):
        return self._clients.get(name)

    def get_client_for_tool(self, tool_name: str) -> Optional:
        for prefix, client_name in self._tool_prefix_map.items():
            if tool_name.startswith(prefix):
                return self._clients.get(client_name)
        return None

    def get_all_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for client in self._clients.values():
            tools.extend(client.get_tools())
        return tools

    def get_risk_level(self, tool_name: str) -> str:
        mcp_name = self._mcp_tool_alias.get(tool_name)
        if mcp_name:
            tool_name = mcp_name
        client = self.get_client_for_tool(tool_name)
        if client:
            return client.get_risk_level(tool_name)
        if ENABLE_LOCAL_ADAPTER:
            return self._erp_adapter.get_risk_level(tool_name)
        return "SAFE"

    def execute_tool(self, tool_name: str, args: dict) -> dict:
        mcp_name = self._mcp_tool_alias.get(tool_name)
        if mcp_name:
            tool_name = mcp_name
        client = self.get_client_for_tool(tool_name)
        if client:
            return client.execute_tool(tool_name, args)
        if ENABLE_LOCAL_ADAPTER:
            return self._erp_adapter.execute_tool(tool_name, args)
        raise ValueError(tool_not_found(tool_name))

    def get_approval_detail(self, tool_name: str, args: dict) -> dict:
        client = self.get_client_for_tool(tool_name)
        if client:
            return client.get_approval_detail(tool_name, args)
        if ENABLE_LOCAL_ADAPTER:
            return self._erp_adapter.get_approval_detail(tool_name, args)
        raise ValueError(tool_not_found(tool_name))


_client_factory = ClientFactory()


def get_client_factory() -> ClientFactory:
    return _client_factory


def register_client(name: str, client) -> None:
    _client_factory.register_client(name, client)


def register_erp_adapter() -> None:
    _client_factory.register_erp_adapter()


def get_all_tools() -> List[Dict[str, Any]]:
    return _client_factory.get_all_tools()


def get_risk_level(tool_name: str) -> str:
    return _client_factory.get_risk_level(tool_name)


def execute_tool(tool_name: str, args: dict) -> dict:
    return _client_factory.execute_tool(tool_name, args)


def get_approval_detail(tool_name: str, args: dict) -> dict:
    return _client_factory.get_approval_detail(tool_name, args)