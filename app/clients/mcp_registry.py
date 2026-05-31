import json
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, List

from app.clients.mcp_client import MCPClient
from app.clients.client_factory import register_client
from app.config import TIMEOUT_CONFIG, MCP_SERVICE_URL

logger = logging.getLogger(__name__)


class MCPRegistry:
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path
        self._clients: Dict[str, MCPClient] = {}
        self._lock = threading.Lock()
        self._in_flight: Dict[str, threading.Event] = {}

    def initialize(self) -> None:
        if self._config_path:
            self.load_config(self._config_path)
        else:
            self.load_default_config()

    def load_config(self, config_path: str) -> None:
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"mcp_servers.json not found at {config_path}, no MCP services registered")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}")
            return

        mcp_servers = config.get("mcpServers", {})
        self._register_services(mcp_servers)

    def load_default_config(self) -> None:
        default_path = Path(__file__).parent.parent / "config_dir" / "mcp_servers.json"
        if default_path.exists():
            self.load_config(str(default_path))
        else:
            logger.warning(f"Default mcp_servers.json not found, no MCP services registered")

    def _register_services(self, mcp_servers: Dict) -> None:
        for name, service_config in mcp_servers.items():
            service_type = service_config.get("type", "streamableHttp")

            if service_type != "streamableHttp":
                logger.warning(f"Unsupported type '{service_type}' for service '{name}', skipping")
                continue

            config_url = service_config.get("url")
            if not config_url:
                logger.warning(f"Missing required field 'url' for service '{name}', skipping")
                continue

            url = config_url
            url_source = "config"

            if name == "erp" and MCP_SERVICE_URL:
                url = MCP_SERVICE_URL
                url_source = "env"

            headers = service_config.get("headers", {})
            timeout = service_config.get("timeout", TIMEOUT_CONFIG["mcp_request"])

            logger.info(f"Attempting to register MCP service '{name}' at {url} (timeout={timeout}s)")

            try:
                import requests
                health_url = f"{url.rstrip('/')}/health"
                try:
                    health_resp = requests.get(health_url, timeout=3)
                    logger.info(f"MCP service '{name}' health check: {health_resp.status_code}")
                except requests.exceptions.ConnectionError:
                    logger.error(f"MCP service '{name}' at {url} is not reachable (ConnectionError)")
                    logger.error(f"Please ensure the MCP service is running on {url}")
                    raise
                except requests.exceptions.Timeout:
                    logger.error(f"MCP service '{name}' at {url} health check timed out (3s)")
                    raise

                client = MCPClient(
                    name=name,
                    endpoint=url,
                    headers=headers,
                    timeout=timeout
                )
                register_client(name, client)
                self._clients[name] = client
                logger.info(f"MCP service '{name}' registered successfully at {url} (URL from {url_source})")
            except Exception as e:
                error_detail = str(e)
                if hasattr(e, 'args') and len(e.args) > 0:
                    inner = e.args[0]
                    if hasattr(inner, 'message'):
                        error_detail = inner.message
                logger.error(f"Failed to register MCP service '{name}' at {url}: {error_detail}")

    def get_client(self, name: str) -> Optional[MCPClient]:
        return self._clients.get(name)

    def get_client_for_tool(self, tool_name: str) -> Optional[MCPClient]:
        for client_name, client in self._clients.items():
            for tool in client.get_tools():
                tool_def_name = tool.get("name", "")
                if tool_def_name == tool_name:
                    return client
        return None

    def reload(self) -> dict:
        with self._lock:
            added = 0
            removed = 0
            updated = 0
            failed = 0

            old_clients = set(self._clients.keys())

            if self._config_path:
                new_config_path = self._config_path
            else:
                new_config_path = str(Path(__file__).parent.parent / "config_dir" / "mcp_servers.json")

            new_path = Path(new_config_path)
            if not new_path.exists():
                logger.warning(f"Config file not found during reload: {new_config_path}")
                return {"added": 0, "removed": 0, "updated": 0, "failed": 0}

            try:
                with open(new_path, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON during reload: {e}")
                return {"added": 0, "removed": 0, "updated": 0, "failed": 0}

            new_mcp_servers = new_config.get("mcpServers", {})
            new_service_names = set(new_mcp_servers.keys())

            for name in old_clients:
                if name not in new_service_names:
                    self._wait_for_in_flight(name)
                    if name in self._clients:
                        del self._clients[name]
                    removed += 1
                    logger.info(f"Removed MCP service: {name}")

            for name, service_config in new_mcp_servers.items():
                service_type = service_config.get("type", "streamableHttp")
                url = service_config.get("url")

                if name in old_clients:
                    old_client = self._clients.get(name)
                    if old_client and (old_client.endpoint != url.rstrip("/") or
                                        old_client.headers != service_config.get("headers", {}) or
                                        old_client.timeout != service_config.get("timeout", TIMEOUT_CONFIG["mcp_request"])):
                        self._wait_for_in_flight(name)
                        del self._clients[name]
                        updated += 1
                else:
                    added += 1

                if service_type != "streamableHttp":
                    logger.warning(f"Unsupported type '{service_type}' for service '{name}', skipping")
                    continue

                if not url:
                    logger.warning(f"Missing required field 'url' for service '{name}', skipping")
                    failed += 1
                    continue

                headers = service_config.get("headers", {})
                timeout = service_config.get("timeout", TIMEOUT_CONFIG["mcp_request"])

                try:
                    client = MCPClient(
                        name=name,
                        endpoint=url,
                        headers=headers,
                        timeout=timeout
                    )
                    self._clients[name] = client
                    register_client(name, client)
                    logger.info(f"Updated/Added MCP service: {name} -> {url}")
                except Exception as e:
                    logger.error(f"Failed to reload MCP client for '{name}': {e}")
                    failed += 1

            return {"added": added, "removed": removed, "updated": updated, "failed": failed}

    def _wait_for_in_flight(self, client_name: str) -> None:
        event = self._in_flight.get(client_name)
        if event:
            event.wait(timeout=30)

    def mark_in_flight(self, client_name: str) -> threading.Event:
        event = threading.Event()
        self._in_flight[client_name] = event
        return event

    def clear_in_flight(self, client_name: str) -> None:
        if client_name in self._in_flight:
            event = self._in_flight.pop(client_name)
            event.set()


_registry: Optional[MCPRegistry] = None


def init_registry(config_path: Optional[str] = None) -> MCPRegistry:
    global _registry
    _registry = MCPRegistry(config_path)
    _registry.initialize()
    return _registry


def get_registry() -> Optional[MCPRegistry]:
    return _registry


def reload_registry() -> dict:
    if _registry:
        return _registry.reload()
    return {"added": 0, "removed": 0, "updated": 0, "failed": 0}