"""Tool dispatch and normalized tool-failure handling."""
from __future__ import annotations

from typing import Any


class Executor:
    def __init__(self, tools: dict[str, Any], logger: Any) -> None:
        self.tools, self.logger = tools, logger

    def execute(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            return {"success": False, "error": f"Unknown tool: {name}"}
        self.logger.info("[EXECUTOR] Calling %s with %s", name, self._short(input_data))
        try:
            result = tool.execute(input_data)
        except Exception as exc:  # last line of defense for integration boundaries
            result = {"success": False, "error": f"Unhandled {name} exception: {exc}"}
        if not result.get("success"):
            self.logger.warning("[EXECUTOR] %s failed: %s", name, result.get("error"))
        return result

    @staticmethod
    def _short(value: Any, limit: int = 300) -> str:
        rendered = str(value).replace("\n", " ")
        return rendered[:limit] + ("…" if len(rendered) > limit else "")
