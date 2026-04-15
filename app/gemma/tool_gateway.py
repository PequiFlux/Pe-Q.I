from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.domain.errors import PequiFluxError


class ToolGateway:
    """Whitelisted execution gateway for model-issued tool intents."""

    def __init__(self, tools: dict[str, Callable[..., Any]]) -> None:
        self._tools = tools

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise PequiFluxError("TOOL_NOT_ALLOWED", f"Tool not allowed: {tool_name}")
        if not isinstance(arguments, dict):
            raise PequiFluxError("INVALID_TOOL_ARGUMENTS", "Tool arguments must be an object.")
        return self._tools[tool_name](**arguments)

