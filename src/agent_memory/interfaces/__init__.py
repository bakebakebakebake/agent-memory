from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["create_mcp_server", "create_rest_app"]


def __getattr__(name: str) -> Any:
    if name == "create_mcp_server":
        return import_module("agent_memory.interfaces.mcp_server").create_mcp_server
    if name == "create_rest_app":
        return import_module("agent_memory.interfaces.rest_api").create_rest_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
